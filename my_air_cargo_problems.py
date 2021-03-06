from aimacode.logic import PropKB
from aimacode.planning import Action
from aimacode.search import (
    Node, Problem,
)
from aimacode.utils import expr
from lp_utils import (
    FluentState, encode_state, decode_state,
)
from my_planning_graph import PlanningGraph


class AirCargoProblem(Problem):
    def __init__(self, cargos, planes, airports, initial: FluentState, goal: list):
        """

        :param cargos: list of str
            cargos in the problem
        :param planes: list of str
            planes in the problem
        :param airports: list of str
            airports in the problem
        :param initial: FluentState object
            positive and negative literal fluents (as expr) describing initial state
        :param goal: list of expr
            literal fluents required for goal test
        """
        self.state_map = initial.pos + initial.neg
        self.initial_state_TF = encode_state(initial, self.state_map)
        Problem.__init__(self, self.initial_state_TF, goal=goal)
        self.cargos = cargos
        self.planes = planes
        self.airports = airports
        self.actions_list = self.get_actions()

    def get_actions(self):
        '''
        This method creates concrete actions (no variables) for all actions in the problem
        domain action schema and turns them into complete Action objects as defined in the
        aimacode.planning module. It is computationally expensive to call this method directly;
        however, it is called in the constructor and the results cached in the `actions_list` property.

        Returns:
        ----------
        list<Action>
            list of Action objects
        '''

        # TODO create concrete Action objects based on the domain action schema for: Load, Unload, and Fly
        # concrete actions definition: specific literal action that does not include variables as with the schema

        # for example, the action schema 'Load(c, p, a)' can represent the concrete actions 'Load(C1, P1, SFO)'
        # or 'Load(C2, P2, JFK)'.  The actions for the planning problem must be concrete because the problems in
        # forward search and Planning Graphs must use Propositional Logic

        def load_actions():
            '''Create all concrete Load actions and return a list

            :return: list of Action objects
            '''
            loads = []
            # TODO create all load ground actions from the domain Load action
            # triple for loop to get all combos of cargo, plane and airports
            for cargo in self.cargos:
                for plane in self.planes:
                    for airport in self.airports:
                        precond_pos = [expr("At({}, {})".format(cargo, airport))
                        , expr("At({}, {})".format(plane, airport))]
                        precond_neg = []
                        effect_add = [expr("In({}, {})".format(cargo, plane))]
                        effect_rem = [expr("At({}, {})".format(cargo, airport))]
                        load = Action(expr("Load({}, {}, {})".format(cargo, plane, airport)),
                            [precond_pos, precond_neg],
                            [effect_add, effect_rem])
                        loads.append(load)
            return loads

        def unload_actions():
            '''Create all concrete Unload actions and return a list

            :return: list of Action objects
            '''
            unloads = []
            # TODO create all Unload ground actions from the domain Unload action
            # possible better way to do this as load and unload are very similar - possibly refactor
            # using a helper function
            for cargo in self.cargos:
                for plane in self.planes:
                    for airport in self.airports:
                        precond_pos = [expr("In({}, {})".format(cargo, plane))
                        , expr("At({}, {})".format(plane, airport))]
                        precond_neg = []
                        effect_add = [expr("At({}, {})".format(cargo, airport))]
                        effect_rem = [expr("In({}, {})".format(cargo, plane))]
                        unload = Action(expr("Unload({}, {}, {})".format(cargo, plane, airport)),
                            [precond_pos, precond_neg],
                            [effect_add, effect_rem])
                        unloads.append(unload)
            return unloads

        def fly_actions():
            '''Create all concrete Fly actions and return a list

            :return: list of Action objects
            '''
            flys = []
            for fr in self.airports:
                for to in self.airports:
                    if fr != to:
                        for p in self.planes:
                            # create the pre-condition for this fly action to happen. expr function
                            # just makes an instance of an Expression object (in utils)
                            # note this is the only precondition we actually have to add because
                            # the other 2 requried (see readme) or p being a plane and fr being
                            # an airpot are implicit as we are looping through self.airports and
                            # self.planes
                            precond_pos = [expr("At({}, {})".format(p, fr)),
                                           ]
                            # no negative pre-conditions
                            precond_neg = []
                            # the effect given this fly action is taken
                            effect_add = [expr("At({}, {})".format(p, to))]
                            # remove this condition if fly action taken
                            effect_rem = [expr("At({}, {})".format(p, fr))]
                            # puts this all together into an Action object (see planning.py)
                            fly = Action(expr("Fly({}, {}, {})".format(p, fr, to)),
                                         [precond_pos, precond_neg],
                                         [effect_add, effect_rem])
                            # add this to the list of possible fly actions we can do
                            flys.append(fly)
            return flys

        return load_actions() + unload_actions() + fly_actions()

    def actions(self, state: str) -> list:
        """ Return the actions that can be executed in the given state.

        :param state: str
            state represented as T/F string of mapped fluents (state variables)
            e.g. 'FTTTFF'
        :return: list of Action objects
        """
        # TODO implement first decodes the fluent state using LP_utils method decode_state. And then
        # given the decoded state from our fluent map. Then loop through the property actions_list
        # and only add actions in that property that are satisfied at this current state. We do
        # this by getting the current state via the STATE argument. Then we make an instance of 
        # a knowledge base (PropKB) so that we can leverage that structure to ask and see if 
        # given this knowledge base if certain conditions for each action to check are met
        # We create this KB via the pos_sentence method given in the FluentState class. This allows
        # us to put only the positive fluents into our KB and then
        # loop through each action and call check_precond method on each action's arguments using
        # the KB instance we just created based on the STATE string
        current_state = decode_state(state, self.state_map)
        kb = PropKB(current_state.pos_sentence())
        possible_actions = [action for action in self.actions_list if action.check_precond(kb, action.args)]
        return possible_actions

    def result(self, state: str, action: Action):
        """ Return the state that results from executing the given
        action in the given state. The action must be one of
        self.actions(state).

        :param state: state entering node
        :param action: Action applied
        :return: resulting state after action
        """
        # TODO implement

        new_state = FluentState([], [])
        legal_actions = self.actions(state)
        # loop through every possible legal_action from STATE. If go through entire loop then 
        # throw an error as action proposed not a valid one
        for pos_action in legal_actions:
            if action.args != pos_action.args or action.name != pos_action.name:
                continue
            else:
                # get the current state
                current_state = decode_state(state, self.state_map)
                # print("current: ", current_state.pos)
                # print("Current - neg: ", current_state.neg)
                # make a knowledge base object to be used to enact our action onto
                kb = PropKB(current_state.pos_sentence())
                # this then enacts our action onto our knowledge base, updating our KB clauses to
                # reflect the effects this action had on our clauses
                action.act(kb, action.args)
                # note: when we do ACT on an action with KB then if a clause in the KB is no longer
                # true (because of the effect of the action) then this clause is removed from the KB
                # thus we are guranteed that kb.clauses will be only positive fluents thus can use
                # it to assign to our positive fluents list for our FluentState
                new_state.pos = kb.clauses
                # print(new_state.pos)
                # print("Action: ", action.name, action.args)
                # print("KB ", kb.clauses)
                # then populate the negative fluents by getting all of the fluents in the initial 
                # state (before the Action) and then only add the fluents that aren't in the 
                # the new state's positive fluent list
                new_state.neg = [fluent for fluent in current_state.pos+current_state.neg if fluent not in new_state.pos]
                # print("Negative fluents :", new_state.neg)
                return encode_state(new_state, self.state_map)
        raise ValueError("Invalid Action")

    def goal_test(self, state: str) -> bool:
        """ Test the state to see if goal is reached

        :param state: str representing state
        :return: bool
        """
        kb = PropKB()
        kb.tell(decode_state(state, self.state_map).pos_sentence())
        for clause in self.goal:
            if clause not in kb.clauses:
                return False
        return True

    def h_1(self, node: Node):
        # note that this is not a true heuristic
        h_const = 1
        return h_const

    def h_pg_levelsum(self, node: Node):
        '''
        This heuristic uses a planning graph representation of the problem
        state space to estimate the sum of all actions that must be carried
        out from the current state in order to satisfy each individual goal
        condition.
        '''
        # requires implemented PlanningGraph class
        pg = PlanningGraph(self, node.state)
        pg_levelsum = pg.h_levelsum()
        return pg_levelsum

    def h_ignore_preconditions(self, node: Node):
        '''
        This heuristic estimates the minimum number of actions that must be
        carried out from the current state in order to satisfy all of the goal
        conditions by ignoring the preconditions required for an action to be
        executed.
        '''
        # TODO implement (see Russell-Norvig Ed-3 10.2.3  or Russell-Norvig Ed-2 11.2)
        # The problem assumed the only 1 action can satisfy one goal. Unlike in the text where it
        # (in general) is possible to satsify multiple goals with one action. Therefore, all we need
        # to do is find the number of fluent variables in our goal state (ie like At(C1, JFK)) and 
        # that is the number of total goals needed to satisfy goal state. Then we take our current
        # node and take its current state (.state attribute is a string of T' and F's which we can
        # use to decode it into a fluent state) and all its positive fluents and see how many 
        # overlap with our goal state and take the difference between total and overlap
        current_state = decode_state(node.state, self.state_map)
        total_goals = len(self.goal)
        satisfied_goals = len(current_state.pos)
        return total_goals - len(set.intersection(set(self.goal), set(current_state.pos)))


def air_cargo_p1() -> AirCargoProblem:
    cargos = ['C1', 'C2']
    planes = ['P1', 'P2']
    airports = ['JFK', 'SFO']
    pos = [expr('At(C1, SFO)'),
           expr('At(C2, JFK)'),
           expr('At(P1, SFO)'),
           expr('At(P2, JFK)'),
           ]
    neg = [expr('At(C2, SFO)'),
           expr('In(C2, P1)'),
           expr('In(C2, P2)'),
           expr('At(C1, JFK)'),
           expr('In(C1, P1)'),
           expr('In(C1, P2)'),
           expr('At(P1, JFK)'),
           expr('At(P2, SFO)'),
           ]
    init = FluentState(pos, neg)
    goal = [expr('At(C1, JFK)'),
            expr('At(C2, SFO)'),
            ]
    # print("initial: ", pos)
    # print("goal:", goal)
    return AirCargoProblem(cargos, planes, airports, init, goal)


def air_cargo_p2() -> AirCargoProblem:
    # TODO implement Problem 2 definition
    cargos = ['C1', 'C2', 'C3']
    planes = ['P1', 'P2', 'P3']
    airports = ['SFO', 'JFK', 'ATL']
    pos = [expr('At(C1, SFO)'), expr('At(C2,JFK)'), expr('At(C3, ATL)')
        , expr('At(P1, SFO)'), expr('At(P2, JFK)'), expr('At(P3, ATL)')]
    neg = [expr('At(C1, JFK)'), expr('At(C1, ATL)'), expr('At(C2, ATL)')
        , expr('At(C2, SFO)'), expr('At(C3, SFO)'), expr('At(C3, JFK)')
        , expr('At(P1, ATL)'), expr('At(P1, JFK)'), expr('At(P2, ATL)')
        , expr('At(P2, SFO)'), expr('At(P3, JFK)'), expr('At(P3, SFO)')
        , expr('In(C1, P1)'), expr('In(C1, P2)'), expr('In(C1, P3)')
        , expr('In(C2, P1)'), expr('In(C2, P2)'), expr('In(C2, P3)')
        , expr('In(C3, P1)'), expr('In(C3, P2)'), expr('In(C3, P3)')]
    goal = [expr('At(C1,JFK)'), expr('At(C2, SFO)'), expr('At(C3, SFO)')]
    initial = FluentState(pos, neg)
    # print("initial: ", pos)
    # print("goal:", goal)
    return AirCargoProblem(cargos, planes, airports, initial, goal)


def air_cargo_p3() -> AirCargoProblem:
    # TODO implement Problem 3 definition
    cargos = ['C1', 'C2', 'C3', 'C4']
    planes = ['P1', 'P2']
    airports = ['SFO', 'JFK', 'ATL', 'ORD']
    pos = [expr('At(C1, SFO)'), expr('At(C2, JFK)'), expr('At(C3, ATL)')
        , expr('At(C4, ORD)'), expr('At(P1, SFO)'), expr('At(P2, JFK)')]
    neg = [expr('At(C1, JFK)'), expr('At(C1, ATL)'), expr('At(C1, ORD)')
        , expr('At(C2, SFO)'), expr('At(C2, ATL)'), expr('At(C2, ORD)')
        , expr('At(C3, SFO)'), expr('At(C3, JFK)'), expr('At(C3, ORD)')
        , expr('At(C4, SFO)'), expr('At(C4, JFK)'), expr('At(C4, ATL)')
        , expr('In(C1, P1)'), expr('In(C1, P2)'), expr('In(C2, P1)')
        , expr('In(C2, P2)'), expr('In(C3, P1)'), expr('In(C3, P2)')
        , expr('In(C4, P1)'), expr('In(C4, P2)')
        , expr('At(P1, JFK)'), expr('At(P1, ATL)'), expr('At(P1, ORD)')
        , expr('At(P2, SFO)'), expr('At(P2, ATL)'), expr('At(P2, ORD)')]
    goal = [expr('At(C1, JFK)'), expr('At(C3, JFK)'), expr('At(C2, SFO)')
        , expr('At(C4, SFO) ')]
    initial = FluentState(pos, neg)
    # print("initial: ", pos)
    # print("goal:", goal)
    return AirCargoProblem(cargos, planes, airports, initial, goal)
