from aimacode.planning import Action
from aimacode.search import Problem
from aimacode.utils import expr
from lp_utils import decode_state


class PgNode():
    ''' Base class for planning graph nodes.

    includes instance sets common to both types of nodes used in a planning graph
    parents: the set of nodes in the previous level
    children: the set of nodes in the subsequent level
    mutex: the set of sibling nodes that are mutually exclusive with this node
    '''

    def __init__(self):
        self.parents = set()
        self.children = set()
        self.mutex = set()

    def is_mutex(self, other) -> bool:
        ''' Boolean test for mutual exclusion

        :param other: PgNode
            the other node to compare with
        :return: bool
            True if this node and the other are marked mutually exclusive (mutex)
        '''
        if other in self.mutex:
            return True
        return False

    def show(self):
        ''' helper print for debugging shows counts of parents, children, siblings

        :return:
            print only
        '''
        print("{} parents".format(len(self.parents)))
        print("{} children".format(len(self.children)))
        print("{} mutex".format(len(self.mutex)))


class PgNode_s(PgNode):
    '''
    A planning graph node representing a state (literal fluent) from a planning
    problem.

    Args:
    ----------
    symbol : str
        A string representing a literal expression from a planning problem
        domain.

    is_pos : bool
        Boolean flag indicating whether the literal expression is positive or
        negative.
    '''

    def __init__(self, symbol: str, is_pos: bool):
        ''' S-level Planning Graph node constructor

        :param symbol: expr
        :param is_pos: bool
        Instance variables calculated:
            literal: expr
                    fluent in its literal form including negative operator if applicable
        Instance variables inherited from PgNode:
            parents: set of nodes connected to this node in previous A level; initially empty
            children: set of nodes connected to this node in next A level; initially empty
            mutex: set of sibling S-nodes that this node has mutual exclusion with; initially empty
        '''
        PgNode.__init__(self)
        self.symbol = symbol
        self.is_pos = is_pos
        self.literal = expr(self.symbol)
        if not self.is_pos:
            self.literal = expr('~{}'.format(self.symbol))

    def show(self):
        '''helper print for debugging shows literal plus counts of parents, children, siblings

        :return:
            print only
        '''
        print("\n*** {}".format(self.literal))
        PgNode.show(self)

    def __eq__(self, other):
        '''equality test for nodes - compares only the literal for equality

        :param other: PgNode_s
        :return: bool
        '''
        if isinstance(other, self.__class__):
            return (self.symbol == other.symbol) \
                   and (self.is_pos == other.is_pos)

    def __hash__(self):
        return hash(self.symbol) ^ hash(self.is_pos)


class PgNode_a(PgNode):
    '''A-type (action) Planning Graph node - inherited from PgNode
    '''

    def __init__(self, action: Action):
        '''A-level Planning Graph node constructor

        :param action: Action
            a ground action, i.e. this action cannot contain any variables
        Instance variables calculated:
            An A-level will always have an S-level as its parent and an S-level as its child.
            The preconditions and effects will become the parents and children of the A-level node
            However, when this node is created, it is not yet connected to the graph
            prenodes: set of *possible* parent S-nodes
            effnodes: set of *possible* child S-nodes
            is_persistent: bool   True if this is a persistence action, i.e. a no-op action
        Instance variables inherited from PgNode:
            parents: set of nodes connected to this node in previous S level; initially empty
            children: set of nodes connected to this node in next S level; initially empty
            mutex: set of sibling A-nodes that this node has mutual exclusion with; initially empty
       '''
        PgNode.__init__(self)
        self.action = action
        self.prenodes = self.precond_s_nodes()
        self.effnodes = self.effect_s_nodes()
        self.is_persistent = False
        if self.prenodes == self.effnodes:
            self.is_persistent = True

    def show(self):
        '''helper print for debugging shows action plus counts of parents, children, siblings

        :return:
            print only
        '''
        print("\n*** {}{}".format(self.action.name, self.action.args))
        PgNode.show(self)

    def precond_s_nodes(self):
        '''precondition literals as S-nodes (represents possible parents for this node).
        It is computationally expensive to call this function; it is only called by the
        class constructor to populate the `prenodes` attribute.

        :return: set of PgNode_s
        '''
        nodes = set()
        for p in self.action.precond_pos:
            n = PgNode_s(p, True)
            nodes.add(n)
        for p in self.action.precond_neg:
            n = PgNode_s(p, False)
            nodes.add(n)
        return nodes

    def effect_s_nodes(self):
        '''effect literals as S-nodes (represents possible children for this node).
        It is computationally expensive to call this function; it is only called by the
        class constructor to populate the `effnodes` attribute.

        :return: set of PgNode_s
        '''
        nodes = set()
        for e in self.action.effect_add:
            n = PgNode_s(e, True)
            nodes.add(n)
        for e in self.action.effect_rem:
            n = PgNode_s(e, False)
            nodes.add(n)
        return nodes

    def __eq__(self, other):
        '''equality test for nodes - compares only the action name for equality

        :param other: PgNode_a
        :return: bool
        '''
        if isinstance(other, self.__class__):
            return (self.action.name == other.action.name) \
                   and (self.action.args == other.action.args)

    def __hash__(self):
        return hash(self.action.name) ^ hash(self.action.args)


def mutexify(node1: PgNode, node2: PgNode):
    ''' adds sibling nodes to each other's mutual exclusion (mutex) set. These should be sibling nodes!

    :param node1: PgNode (or inherited PgNode_a, PgNode_s types)
    :param node2: PgNode (or inherited PgNode_a, PgNode_s types)
    :return:
        node mutex sets modified
    '''
    if type(node1) != type(node2):
        raise TypeError('Attempted to mutex two nodes of different types')
    node1.mutex.add(node2)
    node2.mutex.add(node1)

"""
HLI CODE
"""
def is_mutex_relation(node1: PgNode, node2: PgNode):
    """
    checks if there is a mutex relation between these 2 nodes
    :param node1: PgNode (or inherited PgNode_a, PgNode_s types)
    :param node2: PgNode (or inherited PgNode_a, PgNode_s types)
    :return:
        True if mutex relation exists and false if not
    """
    if node1 in node2.mutex:
        return True
    if node2 in node1.mutex:
        raise ValueError("Mutex sets don't seem to match!")
    return False

def get_expressions(action: Action, cond_or_effect='effect'):
    """
    returns a list of expression objects with them properly negated for all effect expressions in 
    an action object's effect_rem list.
    Arg:
        ACTION - the action who we want to return its pre-conditions or effect expressions
        COND_OR_EFFECT - optional argument to tell method whether to return a list of expressions
            for ACTION's pre conditions or effects
    Return:
        A list of expression objects related to ACTION (with negated expressions properly expressed
            as negated expression objects)
    """ 
    if cond_or_effect == 'effect':
        return action.effect_add + [~effect for effect in action.effect_rem]
    elif cond_or_effect == 'cond':
        return action.precond_pos + [~cond for cond in action.precond_neg]

"""
HLI CODE ends
"""

class PlanningGraph():
    '''
    A planning graph as described in chapter 10 of the AIMA text. The planning
    graph can be used to reason about 
    '''

    def __init__(self, problem: Problem, state: str, serial_planning=True):
        '''
        :param problem: PlanningProblem (or subclass such as AirCargoProblem or HaveCakeProblem)
        :param state: str (will be in form TFTTFF... representing fluent states)
        :param serial_planning: bool (whether or not to assume that only one action can occur at a time)
        Instance variable calculated:
            fs: FluentState
                the state represented as positive and negative fluent literal lists
            all_actions: list of the PlanningProblem valid ground actions combined with calculated no-op actions
            s_levels: list of sets of PgNode_s, where each set in the list represents an S-level in the planning graph
            a_levels: list of sets of PgNode_a, where each set in the list represents an A-level in the planning graph
        '''
        self.problem = problem
        self.fs = decode_state(state, problem.state_map)
        self.serial = serial_planning
        self.all_actions = self.problem.actions_list + self.noop_actions(self.problem.state_map)
        self.s_levels = []
        self.a_levels = []
        self.create_graph()

    def noop_actions(self, literal_list):
        '''create persistent action for each possible fluent

        "No-Op" actions are virtual actions (i.e., actions that only exist in
        the planning graph, not in the planning problem domain) that operate
        on each fluent (literal expression) from the problem domain. No op
        actions "pass through" the literal expressions from one level of the
        planning graph to the next.

        The no-op action list requires both a positive and a negative action
        for each literal expression. Positive no-op actions require the literal
        as a positive precondition and add the literal expression as an effect
        in the output, and negative no-op actions require the literal as a
        negative precondition and remove the literal expression as an effect in
        the output.

        This function should only be called by the class constructor.

        :param literal_list:
        :return: list of Action
        '''
        action_list = []
        for fluent in literal_list:
            act1 = Action(expr("Noop_pos({})".format(fluent)), ([fluent], []), ([fluent], []))
            action_list.append(act1)
            act2 = Action(expr("Noop_neg({})".format(fluent)), ([], [fluent]), ([], [fluent]))
            action_list.append(act2)
        return action_list

    def create_graph(self):
        ''' build a Planning Graph as described in Russell-Norvig 3rd Ed 10.3 or 2nd Ed 11.4

        The S0 initial level has been implemented for you.  It has no parents and includes all of
        the literal fluents that are part of the initial state passed to the constructor.  At the start
        of a problem planning search, this will be the same as the initial state of the problem.  However,
        the planning graph can be built from any state in the Planning Problem

        This function should only be called by the class constructor.

        :return:
            builds the graph by filling s_levels[] and a_levels[] lists with node sets for each level
        '''
        # the graph should only be built during class construction
        if (len(self.s_levels) != 0) or (len(self.a_levels) != 0):
            raise Exception(
                'Planning Graph already created; construct a new planning graph for each new state in the planning sequence')

        # initialize S0 to literals in initial state provided.
        leveled = False
        level = 0
        self.s_levels.append(set())  # S0 set of s_nodes - empty to start
        # for each fluent in the initial state, add the correct literal PgNode_s
        for literal in self.fs.pos:
            self.s_levels[level].add(PgNode_s(literal, True))
        for literal in self.fs.neg:
            self.s_levels[level].add(PgNode_s(literal, False))
        # no mutexes at the first level

        # continue to build the graph alternating A, S levels until last two S levels contain the same literals,
        # i.e. until it is "leveled"
        while not leveled:
            self.add_action_level(level)
            self.update_a_mutex(self.a_levels[level])

            level += 1
            self.add_literal_level(level)
            self.update_s_mutex(self.s_levels[level])

            if self.s_levels[level] == self.s_levels[level - 1]:
                leveled = True

    def add_action_level(self, level):
        ''' add an A (action) level to the Planning Graph

        :param level: int
            the level number alternates S0, A0, S1, A1, S2, .... etc the level number is also used as the
            index for the node set lists self.a_levels[] and self.s_levels[]
        :return:
            adds A nodes to the current level in self.a_levels[level]
        '''
        # TODO add action A level to the planning graph as described in the Russell-Norvig text
        # 1. determine what actions to add and create those PgNode_a objects
        # 2. connect the nodes to the previous S literal level
        # for example, the A0 level will iterate through all possible actions for the problem and add a PgNode_a to a_levels[0]
        #   set iff all prerequisite literals for the action hold in S0.  This can be accomplished by testing
        #   to see if a proposed PgNode_a has prenodes that are a subset of the previous S level.  Once an
        #   action node is added, it MUST be connected to the S node instances in the appropriate s_level set.

        # this method called by create_graph. So should assume that the previous levels have been
        # built along. Don't need to worry about mutex relations as we are just building out the
        # over-arching potential set of actions that can be taken at this level - note some pairs 
        # of actions in each level cannot be done at same time due to mutex relations but this
        # method is not concerned with that. Note that since S(i) is the set of all possible
        # literals. Need to create Action nodes as the SELF.ALL_ACTIONS is a list of Action objects
        # and note nodes. And also because actions at different levels will have different
        # attributes like their parents and children etc..
        if level < 0:
            raise ValueError("Not a valid level in planning graph")
        new_actions = set()
        for action in self.all_actions:
            # first need to turn actions into action nodes
            new_action_node = PgNode_a(action)
            # is this check required? Basically trying to make sure that I don't include actions
            # that have multiple pre-condition literals and any pairs of these literals have mutex
            # relations with one another meaning that both preconditions cannot be satisfied at 
            # this level and thus should not add this action to LEVEL
            mutux_exists = False
            # checking subset checks on the values and not the actual objects. Ie if you have two
            # datetime objects with the same exact date value but are different objects and put them
            # in different sets then if you do set comparison it will say there's an intersection
            if new_action_node.prenodes <= self.s_levels[level]:
                # if len(new_action_node.prenodes) > 1:
                #     node = new_action_node.prenodes[0]
                #     for other_node in new_action_node.prenodes[1:]:
                #         if is_mutex_relation(node, other_node):
                #             mutux_exists = True
                # if not mutux_exists:
                    # adding the S nodes in the same level to the parents to this action node
                    # because it comes before the action node and all these nodes needed to lead
                    # to this action node - maybe shouldn't do this as not really applicable as
                    # action node sometimes require multiple literal nodes in order to happen? so
                    # the notion of parent node not really applicable (??) - > i think it is 
                    # applicable as all of these literal nodes together present at a previous level
                    # can be seen as a parent 'node'.
                new_action_node.parents = new_action_node.prenodes
                new_actions.add(new_action_node)
        self.a_levels.append(new_actions)



    def add_literal_level(self, level):
        ''' add an S (literal) level to the Planning Graph

        :param level: int
            the level number alternates S0, A0, S1, A1, S2, .... etc the level number is also used as the
            index for the node set lists self.a_levels[] and self.s_levels[]
        :return:
            adds S nodes to the current level in self.s_levels[level]
        '''
        # TODO add literal S level to the planning graph as described in the Russell-Norvig text
        # 1. determine what literals to add
        # 2. connect the nodes
        # for example, every A node in the previous level has a list of S nodes in effnodes that represent the effect
        #   produced by the action.  These literals will all be part of the new S level.  Since we are working with sets, they
        #   may be "added" to the set without fear of duplication.  However, it is important to then correctly create and connect
        #   all of the new S nodes as children of all the A nodes that could produce them, and likewise add the A nodes to the
        #   parent sets of the S nodes
        new_literals = set()
        for action_node in self.a_levels[level-1]:
            for effect_node in action_node.effnodes:
                # don't need to make a new literal node object because the literal node object is
                # created when we first create the corresponding action node and it creates 
                # literal nodes that it can lead to if this action taken. Thus we just need to 
                # update the effect_node's parents and add this node to the children of this 
                # action node
                action_node.children.add(effect_node)
                new_literals.add(effect_node)
        for node in new_literals:
            for action_node in self.a_levels[level-1]:
                if node in action_node.effnodes:
                    node.parents.add(action_node)
        self.s_levels.append(new_literals)


    def update_a_mutex(self, nodeset):
        ''' Determine and update sibling mutual exclusion for A-level nodes

        Mutex action tests section from 3rd Ed. 10.3 or 2nd Ed. 11.4
        A mutex relation holds between two actions a given level
        if the planning graph is a serial planning graph and the pair are nonpersistence actions
        or if any of the three conditions hold between the pair:
           Inconsistent Effects
           Interference
           Competing needs

        :param nodeset: set of PgNode_a (siblings in the same level)
        :return:
            mutex set in each PgNode_a in the set is appropriately updated
        '''
        nodelist = list(nodeset)
        for i, n1 in enumerate(nodelist[:-1]):
            for n2 in nodelist[i + 1:]:
                if (self.serialize_actions(n1, n2) or
                        self.inconsistent_effects_mutex(n1, n2) or
                        self.interference_mutex(n1, n2) or
                        self.competing_needs_mutex(n1, n2)):
                    mutexify(n1, n2)

    def serialize_actions(self, node_a1: PgNode_a, node_a2: PgNode_a) -> bool:
        '''
        Test a pair of actions for mutual exclusion, returning True if the
        planning graph is serial, and if either action is persistent; otherwise
        return False.  Two serial actions are mutually exclusive if they are
        both non-persistent.

        :param node_a1: PgNode_a
        :param node_a2: PgNode_a
        :return: bool
        '''
        #
        if not self.serial:
            return False
        if node_a1.is_persistent or node_a2.is_persistent:
            return False
        return True

    def inconsistent_effects_mutex(self, node_a1: PgNode_a, node_a2: PgNode_a) -> bool:
        '''
        Test a pair of actions for inconsistent effects, returning True if
        one action negates an effect of the other, and False otherwise.

        HINT: The Action instance associated with an action node is accessible
        through the PgNode_a.action attribute. See the Action class
        documentation for details on accessing the effects and preconditions of
        an action.

        :param node_a1: PgNode_a
        :param node_a2: PgNode_a
        :return: bool
        '''
        # TODO test for Inconsistent Effects between nodes
        # this is a list of all expressions for NODE_A1. Will use this to check if any of the 
        # effect expressions is the negation of one of the effect expressions of node 2. Just 
        # need one of the effect expressions to be negation of each other than we know there is
        # an inconsistent_effects_mutex relation. Note: weneed to actually negate the expressions
        # in effect_rem because these are represented as positive expressions but just live 
        # in a 'negative expression list' in an Action object thus we know these should actually be
        # the negative expression value
        effects1 = get_expressions(node_a1.action) + [child.literal for child in node_a1.children]
        effects2 = get_expressions(node_a2.action) + [child.literal for child in node_a2.children]
        for effect in effects1:
            for effect2 in effects2:
                # note we can simply do this because udacity has overridden the equals built in
                # method for expressions see line 412 of utils.py to just be if the expression is
                # the same and not the actual expression object. Also, see line 365 of utils.py
                # to see that the built in invert method (denoted in python by ~) has been to 
                # negate the expression. 
                # (??) better way to do this? Why is a negated expression's args a tuple?
                if (effect.op == "~" and effect2.op != "~"):
                    if effect.args[0] == effect2:
                        return True
                if (effect.op != "~" and effect2.op == "~"):
                    if effect == effect2.args[0]:
                        return True

        return False

    def interference_mutex(self, node_a1: PgNode_a, node_a2: PgNode_a) -> bool:
        '''
        Test a pair of actions for mutual exclusion, returning True if the 
        effect of one action is the negation of a precondition of the other.

        HINT: The Action instance associated with an action node is accessible
        through the PgNode_a.action attribute. See the Action class
        documentation for details on accessing the effects and preconditions of
        an action.

        :param node_a1: PgNode_a
        :param node_a2: PgNode_a
        :return: bool
        '''
        # TODO test for Interference between nodes
        # get the preconditions for action 1 and action 2
        preconds1 = get_expressions(node_a1.action, 'cond') + [parent.literal for parent in node_a1.parents]
        preconds2 = get_expressions(node_a2.action, 'cond') + [parent.literal for parent in node_a2.parents]
        effects1 = get_expressions(node_a1.action) + [child.literal for child in node_a1.children]
        effects2 = get_expressions(node_a2.action) + [child.literal for child in node_a2.children]
        # loop through action 1's preconditions and see if any of those equal the negated value 
        # of any of the effects of action 2 (if so there exists a mutex relation)
        # (??) better way to do this? Negated a negated expressions just does ~~Have(Cake) instead
        # of making it positive so this was my way of solving that problem. Because if tried to 
        # check if a positive literal equalled the negated negative literal it would return false
        # because the negated negative literal would be ~~ vs. just the positive literal version
        for precond in preconds1:
            for effect in effects2:
                if (precond.op == "~" and effect.op != "~"):
                    if precond.args[0] == effect:
                        return True
                if (precond.op != "~" and effect.op == "~"):
                    if precond == effect.args[0]:
                        return True
        for precond in preconds2:
            for effect in effects1:
                if (precond.op == "~" and effect.op != "~"):
                    if precond.args[0] == effect:
                        return True
                if (precond.op != "~" and effect.op == "~"):
                    if precond == effect.args[0]:
                        return True
        return False

    def competing_needs_mutex(self, node_a1: PgNode_a, node_a2: PgNode_a) -> bool:
        '''
        Test a pair of actions for mutual exclusion, returning True if one of
        the precondition of one action is mutex with a precondition of the
        other action.

        :param node_a1: PgNode_a
        :param node_a2: PgNode_a
        :return: bool
        '''

        # TODO test for Competing Needs between nodes
        # [print(parent.literal) for parent in node_a1.parents]
        # preconds1 = get_expressions(node_a1.action, 'cond') + [parent.literal for parent in node_a1.parents]
        # preconds2 = get_expressions(node_a2.action, 'cond') + [parent.literal for parent in node_a2.parents]
        preconds1 = node_a1.parents
        preconds2 = node_a2.parents
        # [print(parent.literal) for parent in node_a1.parents]
        # print("actions: ", node_a1.action.name, node_a2.action.name)
        # print("actual preconditions 1: ", node_a1.action.precond_pos, node_a1.action.precond_neg)
        # print("actual preconditions 2: ", node_a2.action.precond_pos, node_a2.action.precond_neg)
        # print("precond1 list:",preconds1)
        # print("precond2 list:",preconds2)
        # print(node_a1.is_mutex(node_a2))
        # basically the same as inconsistent effects mutex relation check but with preconditions
        for precond in preconds1:
            for precond2 in preconds2:
                if precond.is_mutex(precond2):
                    return True

        return False

    def update_s_mutex(self, nodeset: set):
        ''' Determine and update sibling mutual exclusion for S-level nodes

        Mutex action tests section from 3rd Ed. 10.3 or 2nd Ed. 11.4
        A mutex relation holds between literals at a given level
        if either of the two conditions hold between the pair:
           Negation
           Inconsistent support

        :param nodeset: set of PgNode_a (siblings in the same level)
        :return:
            mutex set in each PgNode_a in the set is appropriately updated
        '''
        nodelist = list(nodeset)
        for i, n1 in enumerate(nodelist[:-1]):
            for n2 in nodelist[i + 1:]:
                if self.negation_mutex(n1, n2) or self.inconsistent_support_mutex(n1, n2):
                    mutexify(n1, n2)

    def negation_mutex(self, node_s1: PgNode_s, node_s2: PgNode_s) -> bool:
        '''
        Test a pair of state literals for mutual exclusion, returning True if
        one node is the negation of the other, and False otherwise.

        HINT: Look at the PgNode_s.__eq__ defines the notion of equivalence for
        literal expression nodes, and the class tracks whether the literal is
        positive or negative.

        :param node_s1: PgNode_s
        :param node_s2: PgNode_s
        :return: bool
        '''
        # TODO test for negation between nodes. OPPOSITE_BOOLEAN just a boolean with value True
        # when the nodes have differing 'signs'. then return if their symbols are the same and 
        # their 'signs' differ because that means they are the negation of each other. Allowed to 
        # do this without going into the expression because of how PgNode is structed
        opposite_boolean = ((node_s1.is_pos and not node_s2.is_pos) or (not node_s1.is_pos and node_s2.is_pos))
        return node_s1.symbol == node_s2.symbol and opposite_boolean

    def inconsistent_support_mutex(self, node_s1: PgNode_s, node_s2: PgNode_s):
        '''
        Test a pair of state literals for mutual exclusion, returning True if
        there are no actions that could achieve the two literals at the same
        time, and False otherwise.  In other words, the two literal nodes are
        mutex if all of the actions that could achieve the first literal node
        are pairwise mutually exclusive with all of the actions that could
        achieve the second literal node.

        HINT: The PgNode.is_mutex method can be used to test whether two nodes
        are mutually exclusive.

        :param node_s1: PgNode_s
        :param node_s2: PgNode_s
        :return: bool
        '''
        # TODO test for Inconsistent Support between nodes. 
        # Used an indicator variable to switch to False if find one pair of parent nodes that 
        # are not mutex. Because since we need every possible pair of parent action nodes to be
        # mutex then if one pair isn't then it isn't inconsistent support in terms of the parent 
        # actions (but could still be inconsistent support if the literals are just mutex with 
            # each other - which is why return the 'or')
        indicator = True
        for parent in node_s1.parents:
            for parent2 in node_s2.parents:
                if not parent.is_mutex(parent2):
                    indicator = False
        return node_s1.is_mutex(node_s2) or indicator

    def h_levelsum(self) -> int:
        '''The sum of the level costs of the individual goals (admissible if goals independent)

        :return: int
        '''
        level_sum = 0
        # TODO implement
        # for each goal in the problem, determine the level cost, then add them together
        # note we can get the goal for the problem by calling self.problem.goal (which is just
        # a list of expressions that all need to be satisfied to reach goal state). Note each 
        # 'level' of s_levels is a set of literal node objects (PgNode_s). we can then retrieve 
        # the expression objects by calling the symbol attribute on each node object 
        # making a blank dictionary to keep track of which goals we have already encountered and
        # when we encounter them record what level it is at
        goal_levels = {}
        unfound_goals = set()
        # first populate the original problem goals into our 'unfound' set. We create S nodes from
        # the given goal expressions for easier comparison to the node objects that are in the 
        # levels iterable
        for goal in self.problem.goal:
            node = PgNode_s(goal, True)
            unfound_goals.add(node)
        # loop through each element in s_levels. Each element is a level of literals. Then check 
        # each level of s_levels
        for index, level in enumerate(self.s_levels):
            found_goals = set()

            for goal in unfound_goals:
                if goal in level:
                        goal_levels[goal] = index
                        found_goals.add(goal)

            unfound_goals = unfound_goals - found_goals
            if not unfound_goals:
                break                    

        for goal in goal_levels:
            level_sum += goal_levels[goal]
        return level_sum
