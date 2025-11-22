using PDDL, SymbolicPlanners
using Gen, GenParticleFilters
using InversePlanning
using JSON3

# Register PDDL array theory
PDDL.Arrays.register!()

include("../src/utils.jl")
include("../src/heuristics.jl")
include("../src/actions.jl")
include("../src/goal_priors.jl")
include("../src/beliefs.jl")
include("../src/plans.jl")

domain_name = "mdkg"

for i in 31:31

    problem_name = domain_name* "_" * string(i)

    println("Problem: ", problem_name)

    #call python scripts for synthesizing the domain, problem, and plan
    synthesis_path = @__DIR__
    problem_path = joinpath(@__DIR__,"..", "dataset", "stimuli", domain_name, problem_name)

    if !isdir(problem_path)
        println("Problem path does not exist: ", problem_path)
        continue
    end

    temp_path = joinpath(@__DIR__,"..", "temp", domain_name, problem_name)

    valid_synthesis = false
    gemini_key_addr = "/Users/lance/Documents/GitHub/gemini.txt"

    num_tries = 0
    max_tries = 3
    while !valid_synthesis && num_tries < max_tries

        # try 
            # # Synthesize the domain, problem, and plan
            synthesis_command = `python3 $(synthesis_path)/synthesis.py --api_addr $(gemini_key_addr) --problem_path $(problem_path)  --destination_folder temp`

            println("Running synthesis command: ", synthesis_command)
            run(synthesis_command) 

            # Load configuration from JSON file
            config_path = joinpath(@__DIR__, "..","temp", domain_name, problem_name, "config.json")
            config = JSON3.read(open(config_path, "r"), Dict{String, Any})


            domain , states = load_domain_states(temp_path)

            state = states[1]

            plan = extract_action(domain,  states)

            # Save the plan to a text file
            plan_path = joinpath(temp_path, "plan.txt")
            open(plan_path, "w") do io
                for action in plan
                    println(io, action)
                end
            end

            println("Plan: ", plan, "\n")

            # goals = [[PDDL.parse_pddl(subgoal) for subgoal in g] for g in config["goals"]]

            # if !check_valid_goals(domain, state, goals, config)
            #     println("Invalid goals for problem $(i)")
            #     error("Invalid goals detected for problem $(i).")
            # end

            valid_synthesis = true

        # catch
        #     # Handle the error
        #     println("Synthesis failed. Retrying...")
        #     # synthesis_command = `python3 $(synthesis_path)/synthesis.py --api_addr $(gemini_key_addr) --problem_path $(problem_path)`

        #     # println("Running synthesis command: ", synthesis_command)
        #     # run(synthesis_command) 
        #     num_tries += 1
        #     sleep(1)  # Optional: Add a delay before retrying
        #     continue
        # end
    end
end


# Load the output_nipe.json file
output_nipe_path = joinpath(@__DIR__, "..", "output_nipe.json")
if isfile(output_nipe_path)
    output_nipe = JSON3.read(open(output_nipe_path, "r"), Dict{String, Any})
    println("Loaded output_nipe.json: ", output_nipe)
else
    println("output_nipe.json not found at path: ", output_nipe_path)
end

domain_name = "mdkg"
for i in 1:2

    if length(output_nipe["problem_$(i)"]) == 0


        problem_name = domain_name* "_" * string(i)

        println("Problem: ", problem_name)

        #call python scripts for synthesizing the domain, problem, and plan
        synthesis_path = @__DIR__
        problem_path = joinpath(@__DIR__,"..", "dataset", "stimuli", domain_name, problem_name)
        temp_path = joinpath(@__DIR__,"..", "temp", domain_name, problem_name)

        valid_synthesis = false
        gemini_key_addr = "/Users/lance/Documents/GitHub/gemini.txt"

        num_tries = 0
        max_tries = 3
        while !valid_synthesis && num_tries < max_tries

            try 
                # # Synthesize the domain, problem, and plan
                synthesis_command = `python3 $(synthesis_path)/synthesis.py --api_addr $(gemini_key_addr) --problem_path $(problem_path)`

                println("Running synthesis command: ", synthesis_command)
                run(synthesis_command) 

                # Load configuration from JSON file
                config_path = joinpath(@__DIR__, "..","temp", domain_name, problem_name, "config.json")
                config = JSON3.read(open(config_path, "r"), Dict{String, Any})


                domain , states = load_domain_states(temp_path)

                state = states[1]

                plan = extract_action(domain,  states)

                # Save the plan to a text file
                plan_path = joinpath(temp_path, "plan.txt")
                open(plan_path, "w") do io
                    for action in plan
                        println(io, action)
                    end
                end

                println("Plan: ", plan, "\n")

                goals = [[PDDL.parse_pddl(subgoal) for subgoal in g] for g in config["goals"]]

                if !check_valid_goals(domain, state, goals, config)
                    println("Invalid goals for problem $(i)")
                    error("Invalid goals detected for problem $(i).")
                end

                valid_synthesis = true

            catch
                # Handle the error
                println("Synthesis failed. Retrying...")
                # synthesis_command = `python3 $(synthesis_path)/synthesis.py --api_addr $(gemini_key_addr) --problem_path $(problem_path)`

                # println("Running synthesis command: ", synthesis_command)
                # run(synthesis_command) 
                num_tries += 1
                sleep(1)  # Optional: Add a delay before retrying
                continue
            end
        end
    end
end