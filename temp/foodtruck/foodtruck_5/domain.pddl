
(define (domain foodtruck)
    (:requirements :fluents :adl :typing)
    (:types 
        foodtruck parkinglot - item
        item agent - object 
    )
    (:predicates 
        (at ?a - agent ?o - object)
        (adjacent ?a - agent ?o - object)
    )

    (:constants 
        student - agent
        koreantruck mexicantruck lebanesetruck - foodtruck
    )

    (:functions 
        (gridheight) - integer
        (gridwidth) - integer
        (xloc ?o - object) (yloc ?o - object) - integer
        (whitespace) (buildings) - bit-matrix
    )

    (:derived (adjacent ?a ?i)(or (and (= (xloc ?a) (xloc ?i)) (= (- (yloc ?a) 1) (yloc ?i)))
                (and (= (xloc ?a) (xloc ?i)) (= (+ (yloc ?a) 1) (yloc ?i)))
                (and (= (- (xloc ?a) 1) (xloc ?i)) (= (yloc ?a) (yloc ?i)))
                (and (= (+ (xloc ?a) 1) (xloc ?i)) (= (yloc ?a) (yloc ?i)))))


    (:derived (at ?a ?i) (and (= (xloc ?a) (xloc ?i)) (= (yloc ?a) (yloc ?i))))

    (:action up-white
     :parameters (?a - agent)
     :precondition
        (and (> (yloc ?a) 1)
            (= (get-index whitespace (yloc ?a) (xloc ?a)) true)
            (= (get-index buildings (- (yloc ?a) 1) (xloc ?a)) false)
        )
     :effect
        (and (decrease (yloc ?a) 1))
    )

    (:action down-white
     :parameters (?a - agent)
     :precondition
        (and (< (yloc ?a) (gridheight))
            (= (get-index whitespace (yloc ?a)(xloc ?a)) true)
            (= (get-index buildings (+ (yloc ?a) 1) (xloc ?a)) false)
        )
     :effect 
        (and (increase (yloc ?a) 1))
    )

    (:action left-white
     :parameters (?a - agent)
     :precondition
        (and (> (xloc ?a) 1)
            (= (get-index whitespace (yloc ?a) (xloc ?a)) true)
            (= (get-index buildings (yloc ?a) (- (xloc ?a) 1)) false)
        )
     :effect
        (and (decrease (xloc ?a) 1))
    )

    (:action right-white
     :parameters (?a - agent)
     :precondition
        (and (< (xloc ?a) (gridwidth)) 
            (= (get-index whitespace (yloc ?a) (xloc ?a)) true)
            (= (get-index buildings (yloc ?a) (+ (xloc ?a) 1)) false)
        )
     :effect
        (and (increase (xloc ?a) 1))
    )

)
