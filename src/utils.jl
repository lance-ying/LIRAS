using PDDL, SymbolicPlanners
using IterTools
using Combinatorics
using Distributions, Random

"Returns the location of an object."
function get_obj_loc(state::State, obj::Const;)
    x = state[Compound(:xloc, Term[obj])]
    y = state[Compound(:yloc, Term[obj])]
    # Check if object is held by an agent, and return agent's location if so
    return (x, y)
end

"Sets the location of an object."
function set_obj_loc!(state::State, obj::Const, loc::Tuple{Int,Int})
    state[pddl"(xloc $obj)"] = loc[1]
    state[pddl"(yloc $obj)"] = loc[2]
    return loc
end


"Returns the color of an object."
function get_obj_color(state::State, obj::Const)
    for color in PDDL.get_objects(state, :color)
        if state[Compound(:iscolor, Term[obj, color])]
            return color
        end
    end
    return Const(:none)
end


"Return a new PDDL problem with domain constants added as objects."
function add_domain_constants(domain::Domain, problem::GenericProblem)
    constants = PDDL.get_constants(domain)
    constypes = PDDL.get_constypes(domain)
    problem = copy(problem)
    prepend!(problem.objects, constants)
    for c in constants
        problem.objtypes[c] = constypes[c]
    end
    return problem
end

"Return a new PDDL domain with domain constants removed."
function remove_domain_constants(domain::GenericDomain)
    domain = copy(domain)
    empty!(domain.constants)
    empty!(domain.constypes)
    return domain
end

function in_view(domain, state::State, obj, agent, barrier)
    xloc_agent = state[pddl"(xloc $agent)"]
    yloc_agent = state[pddl"(yloc $agent)"]
    xloc_obj = state[pddl"(xloc $obj)"]
    yloc_obj = state[pddl"(yloc $obj)"]

    if xloc_obj == -1 || yloc_obj == -1
        return false
    end

    for i in min(xloc_agent,xloc_obj):max(xloc_agent,xloc_obj)
        for j in min(yloc_agent,yloc_obj):max(yloc_agent,yloc_obj)
            if PDDL.evaluate(domain, state, pddl"(get-index $barrier $j $i)")
                return false
            end
        end
    end
    return true
end

function initialize_configs(domain, state, planner, config, goal_prior)
    # Define action noise model
    
    initial_states = []

    if config["observability"] == "full"

        sampled_value = max(0.5, rand(Normal(1.5, 1.0)))
        act_config = BoltzmannActConfig(sampled_value)

        agent_config = AgentConfig(
            domain, planner;
            # Assume fixed goal over time
            goal_config = StaticGoalConfig(goal_prior),
            # Assume the agent refines its policy at every timestep
            replan_args = (
                plan_at_init = true, # Plan at initial timestep
                prob_replan = 0, # Probability of replanning at each timestep
                prob_refine = 1.0, # Probability of refining solution at each timestep
                rand_budget = false # Search budget is fixed everytime
            ),
        
            act_config = act_config
    
        )
        initial_states = [state]
        initial_belief_dists = [log.([1.0])]

    else

        belief_object = Symbol(config["belief_config"]["belief_object"])
        belief_container = Symbol(config["belief_config"]["belief_container"])
        barrier = Symbol(config["belief_config"]["barrier"])
        agent = Symbol(config["belief_config"]["agent"])

        initial_states = enumerate_possible_envs(domain, state, belief_object, belief_container, agent, barrier)

        initial_belief_dists = enumerate_belief_dists(length(initial_states), 3, no_zeros=true)
        # initial_belief_dists = [log.([1/3, 1/3, 1/3])]

        partial_observation_model = construct_partial_observation_model(belief_object, belief_container, agent, barrier)

        # Define the goal prior
        # print(length(initial_states), "\n")
        # println(length(initial_belief_dists), "\n")

        belief_config = ParticleBeliefConfig(
            domain, partial_observation_model,
            initial_states, initial_belief_dists
        )

        plan_config = ParticleBeliefPolicyConfig(domain, planner)

        act_config = BoltzmannQMDPActConfig(1.0, -10000)

        # Define agent configuration
        agent_config = AgentConfig(
            goal_config = StaticGoalConfig(goal_prior),
            belief_config = belief_config,
            plan_config = plan_config,
            act_config = act_config
            )

    end
    return agent_config, initial_states, initial_belief_dists
end

function check_valid_goals(domain, state, goals, config)

    if config["observability"] == "partial"
        return true
    else
        for goal in goals
            planner = AStarPlanner(GoalManhattan(), max_nodes=2^16)
            # Check if the goal is valid
            sol = planner(domain, state, goal)
            if length(collect(sol)) == 0
                # Check if the goal is reachable

                return false
                end
        end
        return true
end
end

"Uniquify a goal by removing all other goals that are equivalent."
function uniquify_goal(goal, all_goals)
    non_goals = filter(all_goals) do g
        g != goal && PDDL.to_cnf_clauses(g) ⊈ PDDL.to_cnf_clauses(goal)
    end
    println("Non-goals: ", non_goals)
    non_goals = map(t -> Compound(:not, Term[t]), non_goals)
    return Compound(:and, PDDL.flatten_conjs(Term[goal; non_goals]))
end

function initialize_goal_rewards(goals, config)
    size = config["grid_size"]

    multiplier = (size[1] + size[2])/2
    all_predicates = []
    for goal in goals
        for predicate in goal
            if predicate in all_predicates
                continue
            end
            push!(all_predicates, predicate)
        end
    end

    count_subgoals = length(all_predicates)
    subgoal_rewards = []
    push!(subgoal_rewards, 1)
    for i in [4,7]
        push!(subgoal_rewards, multiplier*i)
    end

    # all_possible_vectors = IterTools.product(fill(subgoal_rewards, count_subgoals)...)


    subgoal_reward_set = []
    
    for v in Iterators.product(Iterators.repeated(subgoal_rewards, count_subgoals)...)
        push!(subgoal_reward_set, collect(v))
    end

    goal_rewards_set = []
    for subgoal_reward in subgoal_reward_set
        goal_rewards = []
        for goal in goals
            goal_reward = 0
                for subgoal in goal
                    for i in 1:length(all_predicates)
                        if subgoal == all_predicates[i] && !occursin("spaceship",PDDL.write_pddl(subgoal) )
                            goal_reward += subgoal_reward[i]
                        end
                    end
                end
            push!(goal_rewards, goal_reward)
        end
        push!(goal_rewards_set, goal_rewards)
    end
    return all_predicates, subgoal_reward_set, goal_rewards_set
end



function check_action(domain, state_prev, state_next)
    #get all the actions

    # print("State: ", state_prev, "\n")
    actions = PDDL.available(domain, state_prev)

    # println(actions)
    #check if the action is valid

    action_candidates = []
    for act in actions
        simulated_state = PDDL.transition(domain, state_prev, act)
        flag = true

        for object in PDDL.get_objects(domain, simulated_state, :agent)

            if get_obj_loc(simulated_state, object) != get_obj_loc(state_next, object)
                flag = false
            end
        end

        if flag
            push!(action_candidates, act)
        end
    end

    if length(action_candidates) == 0
        return nothing
    end

    if length(action_candidates) == 1
        return action_candidates[1]
    end

    if length(action_candidates) > 1

        for act in action_candidates
            if !occursin("noop", PDDL.write_pddl(act))
                return act
            end
        end
    end

    return nothing
end



function load_domain_states(temp_path)
    frame_files = filter(f -> occursin("frame", f) && occursin(".pddl", f), readdir(temp_path))
    num_frame_files = length(frame_files)

    states = []



    for i in 0: num_frame_files-1
        domain = load_domain(joinpath(temp_path, "domain.pddl"))
        new_frame = load_problem(joinpath(temp_path, "frame_$(i).pddl"))
        new_frame = add_domain_constants(domain, new_frame)
        domain = remove_domain_constants(domain)
        state = initstate(domain, new_frame)

        push!(states, state)

        
    end

    domain = load_domain(joinpath(temp_path, "domain.pddl"))
    domain = remove_domain_constants(domain)


    return domain, states
        
end

function extract_action(domain, states)
    # temp_dir = joinpath(@__DIR__, "temp", domain_name, problem_name)

    plan::Vector{Term} = []

    # prev_frame = load_problem(joinpath(temp_path, "frame_0.pddl"))

    for i in 1: length(states)-1
        # Load the next frame
        # next_frame = load_problem(joinpath(temp_path, "frame_$(i).pddl"))
        
        # Check if the action is valid
        act = check_action(domain, states[i], states[i+1])

        # print("Action: ", act, "\n")
        
        if act != nothing
            push!(plan, act)
        end
        
    end

    return plan
end


# domain = load_domain(joinpath(temp_path, "domain.pddl"))

# prev_frame = load_problem(joinpath(temp_path, "frame_0.pddl"))



# next_frame = load_problem(joinpath(temp_path, "frame_1.pddl"))

# state_prev = initstate(domain, prev_frame)

# new_problem = add_domain_constants(domain, prev_frame)
# new_domain = remove_domain_constants(domain)

# new_state = initstate(new_domain, new_problem)

# actions = PDDL.available(domain, state_prev)


function initialize_costs(domain, costs)
    # Initialize costs for each action
    action_costs = []
    for cost in costs
        action_cost :: Dict{Symbol, Real} = Dict()
        for action_str in keys(cost)
            action = Symbol(action_str)
            if action in keys(domain.actions)
                # print(typeof(action), "\n")
                # print(String(action))
                # print(Real(cost[String(action)]), "\n")
                action_cost[action] = Real(cost[String(action)])
            else
                # If the action is not in the domain, set its cost to 1
                action_cost[action] = 1.0
            end
        end
        push!(action_costs, action_cost)
    end
    return action_costs
end

function generate_callback(question_type)
    if question_type == "goal"
        return (t, pf) -> t::Int
    elseif question_type == "cost"
        return pf -> probvec(pf, :init => :agent => :goal => :cost_idx)::Vector{Float64}
    elseif question_type == "reward"
        return pf -> probvec(pf, :init => :agent => :goal => :reward_idx)::Vector{Float64}
    elseif question_type == "belief"
        
    else
        error("Invalid question type")
    end
end