(define (domain doors-keys-gems)
    (:requirements :fluents :adl :typing)
    (:types 
        package spacecraft - item
        item agent - object
    )
    (:predicates 
        (has ?a - agent ?i - item)
    )
    (:functions 
        (xloc ?o - object) (yloc ?o - object) - integer
        (walls) - bit-matrix
    )

    (:action pickup
     :parameters (?a - agent ?i - item)
     :precondition
        (and (= (xloc ?a) (xloc ?i)) (= (yloc ?a) (yloc ?i)))
     :effect 
        (and (has ?a ?i) 
            (assign (xloc ?i) -1) (assign (yloc ?i) -1))
    )

    (:action up
     :parameters (?a - agent)
     :precondition
        (> (yloc ?a) 1)
     :effect
        (and (decrease (yloc ?a) 1))
    )

    (:action down
     :parameters (?a - agent)
     :precondition
        (< (yloc ?a) (height walls))
     :effect 
        (and (increase (yloc ?a) 1))
    )

    (:action left
     :parameters (?a - agent)
     :precondition
        (> (xloc ?a) 1)
     :effect
        (and (decrease (xloc ?a) 1))
    )

    (:action right
     :parameters (?a - agent)
     :precondition
        (< (xloc ?a) (width walls)) 
     :effect
        (and (increase (xloc ?a) 1))
    )

)
