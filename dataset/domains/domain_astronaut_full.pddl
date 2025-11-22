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

    (:action up-white
     :parameters (?a - agent)
     :precondition
        (and (> (yloc ?a) 1) (= (get-index whitespace (yloc ?a) (xloc ?a)) true))
     :effect
        (and (decrease (yloc ?a) 1) (= (get-index whitespace (yloc ?a) (xloc ?a)) true))
    )

    (:action down-white
     :parameters (?a - agent)
     :precondition
        (and (< (yloc ?a) (height walls)) (= (get-index whitespace (yloc ?a) (xloc ?a)) true))
     :effect 
        (and (increase (yloc ?a) 1) (= (get-index whitespace (yloc ?a) (xloc ?a)) true))
    )

    (:action left-white
     :parameters (?a - agent)
     :precondition
        (and (> (xloc ?a) 1) (= (get-index whitespace (yloc ?a) (xloc ?a)) true))

     :effect
        (and (decrease (xloc ?a) 1))
    )

    (:action right-white
     :parameters (?a - agent)
     :precondition
        (and (< (xloc ?a) (width walls)) (= (get-index whitespace (yloc ?a) (xloc ?a)) true))

     :effect
        (and (increase (xloc ?a) 1))
    )


    (:action up-blue
     :parameters (?a - agent)
     :precondition
        (and (> (yloc ?a) 1) (= (get-index bluespace (yloc ?a) (xloc ?a)) true))
     :effect
        (decrease (yloc ?a) 1)
    )

    (:action down-blue
     :parameters (?a - agent)
     :precondition
        (and (< (yloc ?a) (height walls)) (= (get-index bluespace (yloc ?a) (xloc ?a)) true))
     :effect 
        (increase (yloc ?a) 1)
    )

    (:action left-blue
     :parameters (?a - agent)
     :precondition
        (and (> (xloc ?a) 1) (= (get-index bluespace (yloc ?a) (xloc ?a)) true))

     :effect
        (and (decrease (xloc ?a) 1))
    )

    (:action right-blue
     :parameters (?a - agent)
     :precondition
        (and (< (xloc ?a) (width walls)) (= (get-index bluespace (yloc ?a) (xloc ?a)) true))
     :effect
        (and (increase (xloc ?a) 1))
    )


    (:action up-pink
     :parameters (?a - agent)
     :precondition
        (and (> (yloc ?a) 1) (= (get-index pinkspace (yloc ?a) (xloc ?a)) true))
     :effect
        (decrease (yloc ?a) 1)
    )

    (:action down-pink
     :parameters (?a - agent)
     :precondition
        (and (< (yloc ?a) (height walls)) (= (get-index pinkspace (yloc ?a) (xloc ?a)) true))
     :effect 
        (increase (yloc ?a) 1)
    )

    (:action left-pink
     :parameters (?a - agent)
     :precondition
        (and (> (xloc ?a) 1) (= (get-index pinkspace (yloc ?a) (xloc ?a)) true))

     :effect
        (and (decrease (xloc ?a) 1))
    )

    (:action right-pink
     :parameters (?a - agent)
     :precondition
        (and (< (xloc ?a) (width walls)) (= (get-index pinkspace (yloc ?a) (xloc ?a)) true))

     :effect
        (and (increase (xloc ?a) 1))
    )


)
