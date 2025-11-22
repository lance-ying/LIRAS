(define (domain doors-keys-gems)
    (:requirements :fluents :adl :typing)
    (:types 
        key gem - item
        robot human - agent
        item door agent - physical
        physical color - object
    )
    (:predicates
        (has ?a - agent ?i - item) 
        (iscolor ?o - physical ?c - color)
        (offgrid ?i - item)
        (locked ?d - door)
    )
    (:functions
        (xloc ?o - physical) (yloc ?o - physical) - integer
        (agentcode ?a - agent) - integer
        (turn)- integer
        (walls)- bit-matrix
    )
    
    (:action pickup
     :parameters (?a - agent ?i - item)
     :precondition (and (not (has ?a ?i)) (= (xloc ?a) (xloc ?i)) (= (yloc ?a) (yloc ?i))(= turn (agentcode ?a)))
     :effect (and (has ?a ?i) (offgrid ?i)
                  (assign (xloc ?i) -1) (assign (yloc ?i) -1) (assign turn (- 1 turn)))
    )

    (:action unlock
     :parameters (?a - agent ?k - key ?d - door)
     :precondition (and (has ?a ?k) (locked ?d)
                        (= turn (agentcode ?a))
                        (exists (?c - color) (and (iscolor ?k ?c) (iscolor ?d ?c)))
                        (or (and (= (xloc ?a) (xloc ?d)) (= (- (yloc ?a) 1) (yloc ?d)))
                            (and (= (xloc ?a) (xloc ?d)) (= (+ (yloc ?a) 1) (yloc ?d)))
                            (and (= (- (xloc ?a) 1) (xloc ?d)) (= (yloc ?a) (yloc ?d)))
                            (and (= (+ (xloc ?a) 1) (xloc ?d)) (= (yloc ?a) (yloc ?d)))))
     :effect (and (not (has ?a ?k)) (not (locked ?d)) (assign turn (- 1  turn)))
    )

    (:action up
     :parameters (?a - agent)
     :precondition
        (and (> (yloc ?a) 1) (= turn (agentcode ?a))
            (= (get-index walls (- (yloc ?a) 1) (xloc ?a)) false)
            (not (exists (?d - door)
                (and (locked ?d) (= (xloc ?a) (xloc ?d)) (= (- (yloc ?a) 1) (yloc ?d))))))
     :effect (and (decrease (yloc ?a) 1) (assign turn (- 1  turn)))
    )
    (:action down
     :parameters (?a - agent)
     :precondition
        (and (< (yloc ?a) (height walls)) (= turn (agentcode ?a))
            (= (get-index walls (+ (yloc ?a) 1) (xloc ?a)) false)
            (not (exists (?d - door)
                (and (locked ?d) (= (xloc ?a) (xloc ?d)) (= (+ (yloc ?a) 1) (yloc ?d))))))
     :effect(and (increase (yloc ?a) 1) (assign turn (- 1  turn)))
    )
    (:action left
     :parameters (?a - agent)
     :precondition
        (and (> (xloc ?a) 1) (= turn (agentcode ?a))
            (= (get-index walls (yloc ?a) (- (xloc ?a) 1)) false)
            (not (exists (?d - door)
                (and (locked ?d) (= (yloc ?a) (yloc ?d)) (= (- (xloc ?a) 1) (xloc ?d))))))
     :effect (and (decrease (xloc ?a) 1) (assign turn (- 1  turn)))
    )
    (:action right
     :parameters (?a - agent)
     :precondition
        (and (< (xloc ?a) (width walls)) (= turn (agentcode ?a))
            (= (get-index walls (yloc ?a) (+ (xloc ?a) 1)) false)
            (not (exists (?d - door)
                (and (locked ?d) (= (yloc ?a) (yloc ?d)) (= (+ (xloc ?a) 1) (xloc ?d))))))
     :effect (and (increase (xloc ?a) 1) (assign turn (- 1 turn)))
    )
    (:action handover
     :parameters (?a - agent ?b - agent ?o - item)
     :precondition
     (and   (has ?a ?o) (= turn (agentcode ?a))
            (or (and (= (xloc ?a) (xloc ?b)) (= (- (yloc ?a) 1) (yloc ?b)))
                (and (= (xloc ?a) (xloc ?b)) (= (+ (yloc ?a) 1) (yloc ?b)))
                (and (= (- (xloc ?a) 1) (xloc ?b)) (= (yloc ?a) (yloc ?b)))
                (and (= (+ (xloc ?a) 1) (xloc ?b)) (= (yloc ?a) (yloc ?b)))))
     :effect (and (not (has ?a ?o)) (has ?b ?o) (assign turn (- 1  turn)))
    )
    (:action noop
     :parameters (?a - agent)
     :precondition
     ((= turn (agentcode ?a)))
     :effect (assign turn (- 1 turn))
    )
)
