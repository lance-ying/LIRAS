# Functions for generating gridworld PDDL problems
using PDDL

"Converts ASCII gridworlds to PDDL problem."
function ascii_to_pddl_foodtruck(
    str::AbstractString,
    name="foodtruck-problem";
)
    objects = Dict(
        :foodtruck => Const[], :parking => Const[], :agent => Const[pddl"(human)"]
    )

    # Parse width and height of grid
    rows = split(str, "\n", keepempty=false)
    width, height = maximum(length.(strip.(rows))), length(rows)
    walls = parse_pddl("(= walls (new-bit-matrix false $height $width))")

    # Parse wall, item, and agent locations
    init = Term[walls]
    init_agent = Term[]
    goal = pddl"(true)"
    for (y, row) in enumerate(rows)
        for (x, char) in enumerate(strip(row))
            if char == '.' # Unoccupied
                continue
            elseif char == 'W' # Wall
                wall = parse_pddl("(= walls (set-index walls true $y $x))")
                push!(init, wall)
            elseif char == 'L'
                n = length(objects[:foodtruck]) + 1
                b = Const(Symbol("lebanese"))
                push!(objects[:foodtruck], b)
                append!(init, parse_pddl("(= (xloc $b) $x)", "(= (yloc $b) $y)"))

                n = length(objects[:parking]) + 1
                k = Const(Symbol("parking$n"))
                # Add key associated with box
                push!(objects[:parking], k)
                append!(init, parse_pddl("(= (xloc $k) $x)", "(= (yloc $k) $y)"))
                push!(init, parse_pddl("(inside $k $b)"))

            elseif char == 'M'
                n = length(objects[:foodtruck]) + 1
                b = Const(Symbol("mexican"))
                push!(objects[:foodtruck], b)
                append!(init, parse_pddl("(= (xloc $b) $x)", "(= (yloc $b) $y)"))

                n = length(objects[:parking]) + 1
                k = Const(Symbol("parking$n"))
                # Add key associated with box
                push!(objects[:parking], k)
                append!(init, parse_pddl("(= (xloc $k) $x)", "(= (yloc $k) $y)"))
                push!(init, parse_pddl("(inside $k $b)"))

            elseif char == 'K'
                n = length(objects[:foodtruck]) + 1
                b = Const(Symbol("korean"))
                push!(objects[:foodtruck], b)
                append!(init, parse_pddl("(= (xloc $b) $x)", "(= (yloc $b) $y)"))

                n = length(objects[:parking]) + 1
                k = Const(Symbol("parking$n"))
                # Add key associated with box
                push!(objects[:parking], k)
                append!(init, parse_pddl("(= (xloc $k) $x)", "(= (yloc $k) $y)"))
                push!(init, parse_pddl("(inside $k $b)"))
            elseif char == 'O'

                n = length(objects[:parking]) + 1
                k = Const(Symbol("parking$n"))
                # Add key associated with box
                push!(objects[:parking], k)
                append!(init, parse_pddl("(= (xloc $k) $x)", "(= (yloc $k) $y)"))

            elseif char == 'A' # Agent
                append!(init_agent, parse_pddl("(= (xloc human) $x)", "(= (yloc human) $y)"))
            end
        end
    end
    append!(init, init_agent)

    # Create object list
    objlist = Const[]
    for objs in values(objects)
        sort!(unique!(objs), by=string)
        append!(objlist, objs)
    end
    # Create object type dictionary
    objtypes = Dict{Const, Symbol}()
    for (type, objs) in objects
        objs = unique(objs)
        for o in objs
            objtypes[o] = type
        end
    end

    problem = GenericProblem(Symbol(name), Symbol("foodtruck"),
                             objlist, objtypes, init, goal,
                             nothing, nothing)
    return problem
end

function load_ascii_problem(path::AbstractString, keyset=nothing)
    str = open(f->read(f, String), path)
    return ascii_to_pddl_foodtruck(str, keyset)
end

function convert_ascii_problem_foodtruck(path::String)
    str = open(f->read(f, String), path)
    str = ascii_to_pddl_foodtruck(str)
    new_path = splitext(path)[1] * ".pddl"
    write(new_path, write_problem(str))
    return new_path
end

function get_filenames()
    path = "/Users/lance/Documents/GitHub/InversePlanningProjects.jl/knowledge_belief_modeling/dataset/problems"
    filenames = readdir(path)
    return filenames
end

filenames = get_filenames()
for filename in filenames
    if endswith(filename, ".txt")
        print(filename)
        convert_ascii_problem("/Users/lance/Documents/GitHub/InversePlanningProjects.jl/knowledge_belief_modeling/dataset/problems/"*filename)
    end
end

convert_ascii_problem_foodtruck("/Users/lance/Documents/GitHub/ToMProjects.jl/NIPE/dataset/problems/foodtruck.txt")
