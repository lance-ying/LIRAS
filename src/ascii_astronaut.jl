# Functions for generating gridworld PDDL problems
using PDDL

"Converts ASCII gridworlds to PDDL problem."
function ascii_to_pddl(
    str::AbstractString,
    key_set::Union{AbstractString, Nothing} = nothing,
    name="astronaut";
)
    objects = Dict(
        :package => Const[], :spacecraft => Const[pddl"(spacecraft)"],
        :agent => Const[pddl"(human)"]
    )

    # Parse width and height of grid
    rows = split(str, "\n", keepempty=false)
    width, height = maximum(length.(strip.(rows))), length(rows)
    walls = parse_pddl("(= walls (new-bit-matrix false $height $width))")

    # Parse wall, item, and agent locations
    init = Term[walls]
    init_agent = Term[]
    goal = pddl"(has astronaut spacecraft)"
    for (y, row) in enumerate(rows)
        for (x, char) in enumerate(strip(row))
            if char == '.' # Unoccupied
                continue
            elseif char == 'A' # Agent
                append!(init_agent, parse_pddl("(= (xloc astronaut) $x)", "(= (yloc astronaut) $y)"))

            elseif char == 'S' # Agent
                append!(init_agent, parse_pddl("(= (xloc spacecraft) $x)", "(= (yloc spacecraft) $y)"))

            elseif char == 'R' # Package
                p = Const(Symbol("redpackage"))
                push!(objects[:package], p)
                append!(init, parse_pddl("(= (xloc $p) $x)", "(= (yloc $p) $y)"))
            elseif char == 'W' # Package
                p = Const(Symbol("whitepackage"))
                push!(objects[:package], p)
                append!(init, parse_pddl("(= (xloc $p) $x)", "(= (yloc $p) $y)"))
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

    problem = GenericProblem(Symbol(name), Symbol("astronaut"),
                             objlist, objtypes, init, goal,
                             nothing, nothing)
    return problem
end

function load_ascii_problem(path::AbstractString, keyset=nothing)
    str = open(f->read(f, String), path)
    return ascii_to_pddl(str, keyset)
end

function convert_ascii_problem(path::String)
    str = open(f->read(f, String), path)
    str = ascii_to_pddl(str)
    new_path = splitext(path)[1] * ".pddl"
    write(new_path, write_problem(str))
    return new_path
end

function get_filenames()
    path = "/Users/lance/Documents/GitHub/InversePlanningProjects.jl/NIPE/dataset/problems"
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

convert_ascii_problem("/Users/lance/Documents/GitHub/ToMProjects.jl/NIPE/dataset/problems/astronaut.txt")


