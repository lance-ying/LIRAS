(define (domain example)
    (:requirements :fluents :adl :typing)
    (:types 
        goal - item
        item agent - object
    )
    (:predicates 
        (has ?a - agent ?i - item)
    )
    (:functions 
        (xloc ?o - physical) (yloc ?o - physical) - integer
        (barriers) - bit-matrix
    )

    (:action pickup
     :parameters (?a - agent ?i - item)
     :precondition
        (and (not (has ?a ?i)) 
            (= (xloc ?a) (xloc ?i)) (= (yloc ?a) (yloc ?i)))
     :effect 
        (and (has ?a ?i)
            (assign (xloc ?i) -1) (assign (yloc ?i) -1)
        )
    )

    (:action up
     :parameters (?a - agent)
     :precondition
        (and (> (yloc ?a) 1)
            (= (get-index barriers (- (yloc ?a) 1) (xloc ?a)) false)
        )
     :effect
        (and (decrease (yloc ?a) 1))
    )

    (:action down
     :parameters (?a - agent)
     :precondition
        (and (< (yloc ?a) (height barriers))
            (= (get-index barriers (+ (yloc ?a) 1) (xloc ?a)) false)
        )
     :effect 
        (and (increase (yloc ?a) 1))
    )

    (:action left
     :parameters (?a - agent)
     :precondition
        (and (> (xloc ?a) 1)
            (= (get-index barriers (yloc ?a) (- (xloc ?a) 1)) false)
        )
     :effect
        (and (decrease (xloc ?a) 1))
    )

    (:action right
     :parameters (?a - agent)
     :precondition
        (and (< (xloc ?a) (width barriers)) 
            (= (get-index barriers (yloc ?a) (+ (xloc ?a) 1)) false)
        )
     :effect
        (and (increase (xloc ?a) 1))
    )
)
