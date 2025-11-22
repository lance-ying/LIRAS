(define (domain doors-keys-gems)
    (:requirements :fluents :adl :typing)
    (:types 
        foodtruck - item
        item agent - object
    )
    (:predicates 
        (has ?a - agent ?i - item)
    )
    (:functions 
        (xloc ?o - physical) (yloc ?o - physical) - integer
        (walls) - bit-matrix
    )

    (:derived (empty ?b) (forall (?i - item) (not (inside ?i ?b))))

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
            (= (get-index walls (- (yloc ?a) 1) (xloc ?a)) false)
            (not (exists (?d - door)
                (and (locked ?d) (= (xloc ?a) (xloc ?d)) (= (- (yloc ?a) 1) (yloc ?d))))))
     :effect
        (and (decrease (yloc ?a) 1))
    )

    (:action down
     :parameters (?a - agent)
     :precondition
        (and (< (yloc ?a) (height walls))
            (= (get-index walls (+ (yloc ?a) 1) (xloc ?a)) false)
            (not (exists (?d - door)
                (and (locked ?d) (= (xloc ?a) (xloc ?d)) (= (+ (yloc ?a) 1) (yloc ?d))))))
     :effect 
        (and (increase (yloc ?a) 1))
    )

    (:action left
     :parameters (?a - agent)
     :precondition
        (and (> (xloc ?a) 1)
            (= (get-index walls (yloc ?a) (- (xloc ?a) 1)) false)
            (not (exists (?d - door)
                 (and (locked ?d) (= (yloc ?a) (yloc ?d)) (= (- (xloc ?a) 1) (xloc ?d))))))
     :effect
        (and (decrease (xloc ?a) 1))
    )

    (:action right
     :parameters (?a - agent)
     :precondition
        (and (< (xloc ?a) (width walls)) 
            (= (get-index walls (yloc ?a) (+ (xloc ?a) 1)) false)
            (not (exists (?d - door)
                 (and (locked ?d) (= (yloc ?a) (yloc ?d)) (= (+ (xloc ?a) 1) (xloc ?d))))))
     :effect
        (and (increase (xloc ?a) 1))
    )

)
