using InversePlanning: softmax

"""Construct a uniform prior over goals, with unit action costs.

Arguments:
- `goals`: A vector of goals, each goal is a vector of terms.
"""
function construct_goal_prior(
    goals::AbstractVector{<:AbstractVector{<:Term}}
)
    @gen function goal_prior()
        goal_idx ~ uniform_discrete(1, length(goals))
        goal = goals[goal_idx]
        return MinStepsGoal(goal)
    end
    return goal_prior
end

"""
Construct a uniform prior over goals and action costs.

Arguments:
- `goals`: A vector of goals, each goal is a vector of terms.
- `action_costs`: A vector of action cost profiles. Each action cost profile is 
    either a `NamedTuple` mapping action names to costs, or a dictionary mapping
    action `Term`s to costs.
"""
function construct_goal_prior_uniform_goal(
    goals::AbstractVector{<:AbstractVector{<:Term}},
    action_costs::AbstractVector
)
    @gen function goal_prior()
        # Sample goal
        goal_idx ~ uniform_discrete(1, length(goals))
        goal = goals[goal_idx]
        # Sample action cost profile
        cost_idx ~ uniform_discrete(1, length(action_costs))
        costs = action_costs[cost_idx]
        return MinActionCosts(goal, costs)
    end
    return goal_prior
end

"""
Construct a uniform prior over goal rewards and action costs. A goal reward and 
action cost profile is combined into an overall reward function that gives a
negative reward for each action (according to the action cost profile) and an
additional positive reward for actions that achieve the goal. Goals are treated
as terminal states, regardless of their rewards.

In order to support planning algorithms like RTHS (which do not support positive
rewards), goal rewards are transformed into negative values. This does not 
affect the resulting optimal policy.

Arguments:
- `goals`: A vector of goals, each goal is a vector of terms.
- `goal_rewards`: A vector of goal reward profiles, each of which is a vector 
    of reward values for achieving each goal.
- `action_costs`: A vector of action cost profiles. Each action cost profile is 
    either a `NamedTuple` mapping action names to costs, or a dictionary mapping
    action `Term`s to costs.
"""
function construct_goal_prior_goal_cost(
    goals::AbstractVector,
    goal_rewards::AbstractVector,
    action_costs::AbstractVector
)
    # Convert each goal into a single term (required by MultiGoalReward)
    goals = [Compound(:and, goal_terms) for goal_terms in goals]
    @gen function goal_prior()
        # Sample goal reward profile
        reward_idx ~ uniform_discrete(1, length(goal_rewards))
        rewards = goal_rewards[reward_idx]
        # Transform goal rewards into negative values
        rewards .-= maximum(rewards)
        # Construct multi-goal reward specification
        spec = MultiGoalReward(goals, rewards)
        # Sample action cost profile
        cost_idx ~ uniform_discrete(1, length(action_costs))
        costs = action_costs[cost_idx]
        # Combine action costs and goal reward specification
        return ExtraActionCosts(spec, costs)
    end
    return goal_prior
end

"""
Construct prior over goals, goals rewards, and action costs. Goals are sampled 
from a Boltzmann distribution, according to the net utility (rewards minus
total costs) of achieving a goal.

To compute the net utility of a goal, a planner is used to compute an optimal
plan to the goal given a sampled action cost profile. The cost of that plan 
is then subtracted from the reward of the goal to obtain the net utility.
Plan costs are precomputed for each action cost profile.

The goal prior returns a MinActionCosts spec, because once a specific goal 
(i.e. terminal state) is chosen, no other goals matter, and their relative 
rewards do not affect planning.

Arguments:
- `domain`: A PDDL domain, required for the planner to compute plans.
- `state`: A PDDL initial state, required for the planner to compute plans.
- `goals`: A vector of goals, each goal is a vector of terms.
- `goal_rewards`: A vector of goal reward profiles, each of which is a vector 
    of reward values for achieving each goal.
- `action_costs`: A vector of action cost profiles. Each action cost profile is 
    either a `NamedTuple` mapping action names to costs, or a dictionary mapping
    action `Term`s to costs.
- `goal_temperature`: The temperature of the Boltzmann distribution over goals.
"""
function construct_goal_prior_full(
    domain::Domain, state::State,
    goals::AbstractVector,
    goal_rewards::AbstractVector,
    action_costs::AbstractVector;
    goal_temperature::Real = 1.0
)
    # Construct RTHS planner with appropriate heuristic and search budget
    # - GoalManhattan is a good choice for gridworlds without diagonal movement
    # - GoalEuclidean is a good choice for gridworlds with diagonal movement
    # - GoalCountHeuristic is a default choice that works across domains
    planner = RTHS(heuristic=GoalCountHeuristic(), max_nodes=2^16,
                   search_neighbors=:none)
    # Precompute plan costs to each goal for each action cost profile
    plan_costs = map(action_costs) do costs
        return map(goals) do goal
            spec = MinActionCosts(goal, costs)
            policy = planner(domain, state, spec)
            optimal_plan_cost = -SymbolicPlanners.get_value(policy, state)
            return optimal_plan_cost
        end
    end
    @gen function goal_prior()
        # Sample goal reward profile
        reward_idx ~ uniform_discrete(1, length(goal_rewards))
        rewards = goal_rewards[reward_idx]
        # Sample action cost profile
        cost_idx ~ uniform_discrete(1, length(action_costs))
        costs = action_costs[cost_idx]
        # Compute net utility of each goal
        goal_utilities = rewards .- plan_costs[cost_idx]
        # Sample goal from Boltzmann distribution
        goal_probs = softmax(goal_utilities ./ goal_temperature)
        goal_idx ~ categorical(goal_probs)
        goal = goals[goal_idx]
        return MinActionCosts(goal, costs)
    end
    return goal_prior
end

