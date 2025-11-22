using PDDL, SymbolicPlanners
using Gen, GenParticleFilters
using InversePlanning
using JSON3



include("src/plan_io.jl")
include("src/utils.jl")
include("src/heuristics.jl")
include("src/actions.jl")
include("src/goal_priors.jl")
include("src/beliefs.jl")
include("src/plans.jl")

# Register PDDL array theory
PDDL.Arrays.register!()


# for i in 1:2

timestep_dict = []
for i in 1:10
    domain_name = "foodtruck"
    problem_name = "foodtruck_$(i)"

    #call python scripts for synthesizing the domain, problem, and plan
    synthesis_path = joinpath(@__DIR__, "synthesis")
    problem_path = joinpath(@__DIR__, "dataset", "stimuli", domain_name, problem_name)
    temp_path = joinpath(@__DIR__, "temp", domain_name, problem_name)



    valid_synthesis = false
    gemini_key_addr = "/Users/lance/Documents/GitHub/gemini.txt"

    num_tries = 0
    max_tries = 5

    start_timestamp = time()
    println("Current UNIX timestamp: ", start_timestamp)
    while !valid_synthesis && num_tries < max_tries

        # try
            # Synthesize the domain, problem, and plan
            # synthesis_command = `python3 $(synthesis_path)/synthesis.py --api_addr $(gemini_key_addr) --problem_path $(problem_path) --destination_folder temp`
            synthesis_command = `python3 $(synthesis_path)/synthesis.py --api_addr $(gemini_key_addr) --problem_path $(problem_path) --destination_folder temp`

            println("Running synthesis command: ", synthesis_command)
            run(synthesis_command)

            # Load configuration from JSON file
            config_path = joinpath(@__DIR__, "temp", domain_name, problem_name, "config.json")
            config = JSON3.read(open(config_path, "r"), Dict{String, Any})


            domain , states = load_domain_states(temp_path)

            state = states[1]

            plan = extract_action(domain,  states)

            goals = [[PDDL.parse_pddl(subgoal) for subgoal in g] for g in config["goals"]]

            if !check_valid_goals(domain, state, goals, config)
                println("Invalid goals for problem $(p_id)")
                error("Invalid goals detected for problem $(p_id).")
            end

            valid_synthesis = true

        # catch
        #     # Handle the error
        #     println("Synthesis failed. Retrying...")
        #     num_tries += 1
        #     sleep(1)  # Optional: Add a delay before retrying
        #     continue
        # end
    end

    config_path = joinpath(@__DIR__, "temp", domain_name, problem_name, "config.json")
    config = JSON3.read(open(config_path, "r"), Dict{String, Any})


    #--- Initial Setup ---#

    domain , states = load_domain_states(temp_path)

    state = states[1]

    plan = extract_action(domain,  states)


    # Load configuration from JSON file
    config_path = joinpath(@__DIR__, "temp", domain_name, problem_name, "config.json")
    config = JSON3.read(open(config_path, "r"), Dict{String, Any})


    # #--- Initial Setup ---#

    # domain , states = load_domain_states(temp_path)

    # state = states[1]

    # plan = extract_action(domain,  states)


    # goals = [[PDDL.parse_pddl(subgoal) for subgoal in g] for g in config["goals"]]

    # print(goals)
    # subgoals, subgoal_rewards, goal_rewards = initialize_goal_rewards(goals, config)



    # costs = initialize_costs(domain, config["costs"])

    # n_goals = length(goals)
    # n_costs = length(costs)
    # n_rewards = length(goal_rewards)

    # goal_prior = construct_goal_prior_goal_cost(goals, goal_rewards, costs)

    # heuristic = GoalManhattan() 

    # # Reuse search results whenever possible when refining the policy with RTHS
    # planner = RTHS(heuristic=heuristic, max_nodes=2^16,
    #             reuse_search=true, reuse_paths=true)
    # # heuristic = GoalManhattan()
    # heuristic = PlannerHeuristic(AStarPlanner(GoalManhattan(), max_nodes=2^16))
    # heuristic = memoized(heuristic)
    # planner = RTHS(heuristic=heuristic, n_iters=0, max_nodes=0)
    # # domain, state = PDDL.compiled(domain, state)

    # agent_config, initial_states, initial_belief_dists = initialize_configs(domain, state, planner, config, goal_prior)

    # n_beliefs = length(initial_belief_dists)

    # # Configure world model with agent configuration and initial state prior
    # world_config = WorldConfig(
    #     agent_config = agent_config,
    #     env_config = PDDLEnvConfig(domain, state),
    #     obs_config = PerfectObsConfig()
    # )

    # ## Run goal and belief inference ##

    # # Construct iterator over initial choicemaps for stratified sampling

    # cost_addr = :init => :agent => :goal => :cost_idx
    # reward_addr = :init => :agent => :goal => :reward_idx
    # belief_addr = :init => :agent => :belief => :belief_id

    # init_strata = choiceproduct((cost_addr, 1:n_costs),
    #                             (reward_addr, 1:n_rewards),
    #                             (belief_addr, 1:n_beliefs))
    # # Construct iterator over observation timesteps and choicemaps 
    # t_obs_iter = act_choicemap_pairs(plan)

    # # Set up logging callback
    # n_goals = length(goals)

    # logger_cb = DataLoggerCallback(
    #     t = (t, pf) -> t::Int,
    #     cost_probs = pf -> probvec(pf, cost_addr, 1:n_costs)::Vector{Float64},
    #     reward_probs = pf -> probvec(pf, reward_addr, 1:n_rewards)::Vector{Float64},
    #     # belief_probs = pf -> probvec(pf, belief_addr, 1:n_beliefs)::Vector{Float64},
    #     mean_initial_belief = (t, pf) -> begin
    #     belief_addr = (:init => :agent => :belief)
    #     traces = get_traces(pf)
    #     trace_probs = get_norm_weights(pf)
    #     mean_belief = sum(zip(traces, trace_probs)) do (trace, p)
    #         belief_state = trace[belief_addr]
    #         belief_dist = exp.(belief_state.log_weights) 
    #         return p .* belief_dist
    #     end
    #     return mean_belief::Vector{Float64}
    # end,
    #     verbose = true
    # )

    # # Configure SIPS particle filter
    # sips = SIPS(world_config, resample_cond=:none, rejuv_cond=:none)

    # # Run particle filter
    # n_samples = length(init_strata)
    # pf_state = sips(
    #     n_samples, t_obs_iter;
    #     init_args = (init_strata = init_strata,),
    #     callback = logger_cb
    # );


    # if "goal" in config["query"]
    #     goal_probs = reduce(hcat, logger_cb.data[:goal_probs])[1:end, end]
    #     println(goal_probs)
    #     data_output_foodtruck["problem_$(i)"]["goal_probs"] = goal_probs
    # end

    # if "cost" in config["query"]
    #     cost_probs = reduce(hcat, logger_cb.data[:cost_probs])[1:end, end]
    #     costs = fill(0.0, length(costs[1]))
    #     for i in 1:length(cost_probs)
    #         for j in 1:length(costs)
    #             costs[j] += cost_probs[i]* costs[i][j]
    #         end
    #     end
    #     println("Costs: ", costs)

    #     data_output_foodtruck["problem_$(i)"]["costs"] = cost_probs
    # end

    # if "reward" in config["query"]
    #     reward_probs = reduce(hcat, logger_cb.data[:reward_probs])[1:end, end]
    #     rewards = fill(0.0, length(goal_rewards[1]))

    #     for i in 1:length(reward_probs)
    #         for j in 1:length(rewards)
    #             rewards[j] += reward_probs[i]* subgoal_rewards[i][j]
    #         end
    #     end
    #     println("Reward: ", rewards)
    #     # data_output_foodtruck["problem_$(i)"]["reward_name"] = subgoals
    #     # data_output_foodtruck["problem_$(i)"]["rewards"] = rewards
    # end

    # if "belief" in config["query"]
    #     belief_probs = reduce(hcat, logger_cb.data[:mean_initial_belief])[1:end, end]
    #     print("Belief probabilities: ", belief_probs, "\n")
    #     # data_output_foodtruck["problem_$(i)"]["belief_probs"] = belief_probs
    # end

    end_timestamp = time()
    println("End UNIX timestamp: ", end_timestamp)
    println("Time taken for problem $(i): ", end_timestamp - start_timestamp, " seconds")
    timestep_dict = push!(timestep_dict, end_timestamp - start_timestamp)
    println("Timestep dict so far: ", timestep_dict)

end

mean_timestep = mean(timestep_dict)
std_timestep = std(timestep_dict)
println("Mean time per problem: ", mean_timestep, " seconds")

