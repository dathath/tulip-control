# Copyright (c) 2013 by California Institute of Technology
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# 3. Neither the name of the California Institute of Technology nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL CALTECH
# OR THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
"""
Transition System Module
"""
from collections import Iterable, OrderedDict
from time import strftime
from pprint import pformat
import copy

from labeled_graphs import LabeledStateDiGraph, str2singleton
from labeled_graphs import prepend_with, vprint
from mathset import PowerSet, MathSet, unique
import automata
from executions import FTSSim

hl = 60 *'-'

class FiniteTransitionSystem(LabeledStateDiGraph):
    """Finite Transition System for modeling closed systems.
    
    Def. 2.1, p.20 [Baier]:
        S = states
        S_0 = initial states \\subseteq states
        
        AP = atomic proposition set (state labels \in 2^AP)
        Act = action set (edge labels)
        
        T = transition relation
          = edge set + edge labeling function
           (transitions labeled by Act)
        L = state labeing function
          : S-> 2^AP
    
    dot export
    ----------
    Format transition labels using C{_transition_dot_label_format} which is a
    dict with values:
        - 'actions' (=name of transitions attribute): type before separator
        - 'type?label': separator between label type and value
        - 'separator': between labels for different sets of actions
            (e.g. sys, env). Not used for closed FTS, because it has single set
            of actions.
    
    note
    ----
    The attributes atomic_propositions and aps are equal.
    When you want to produce readable code, use atomic_propositions.
    Otherwise, aps offers shorthand access to the APs.
    """
    def __init__(self, atomic_propositions=[], actions=[], **args):
        """Note first sets of states in order of decreasing importance,
        then first state labeling, then transitin labeling (states more
        fundamentalthan transitions, because transitions need states in order to
        be defined).
        """
        
        # state labels
        self._state_label_def = OrderedDict(
            [['ap', PowerSet(atomic_propositions) ]]
        )
        self.atomic_propositions = self._state_label_def['ap'].math_set
        self.aps = self.atomic_propositions # shortcut
        self._state_dot_label_format = {'ap':'',
                                           'type?label':'',
                                           'separator':'\\n'}
        
        # edge labels comprised of sublabels (here single sublabel)
        self._transition_label_def = OrderedDict(
            [['actions', MathSet(actions)]]
        )
        self.actions = self._transition_label_def['actions']
        self._transition_dot_label_format = {'actions':'',
                                                'type?label':'',
                                                'separator':'\\n'}
        
        LabeledStateDiGraph.__init__(self, **args)
        
        self.dot_node_shape = {'normal':'box'}
        self.default_export_fname = 'fts'

    def __repr__(self):        
        s = hl +'\nFinite Transition System (closed) : '
        s += self.name +'\n' +hl +'\n'
        s += 'Atomic Propositions:\n\t'
        s += pformat(self.atomic_propositions, indent=3) +2*'\n'
        s += 'States and State Labels (\in 2^AP):\n'
        s += pformat(self.states(data=True), indent=3) +2*'\n'
        s += 'Initial States:\n'
        s += pformat(self.states.initial, indent=3) +2*'\n'
        s += 'Actions:\n\t' +str(self.actions) +2*'\n'
        s += 'Transitions & Labels:\n'
        s += pformat(self.transitions(labeled=True), indent=3)
        s += '\n' +hl +'\n'
        
        return s
    
    def __str__(self):
        return self.__repr__()
    
    def __mul__(self, ts_or_ba):
        """Synchronous product of TS with TS or BA.
        
        see also
        --------
        self.sync_prod
        """
        return self.sync_prod(ts_or_ba)
    
    def __add__(self, other):
        """Merge two Finite Transition Systems.
        
        States, Initial States, Actions, Atomic Propositions and
        State labels and Transitions of the second Transition System
        are merged into the first and take precedence, overwriting
        existing labeling.
        
        example
        -------
        This can be useful to construct systems quickly by
        creating standard "pieces" using the functions:
            line_labeled_with, cycle_labeled_with
        
        >>> n = 4
        >>> L = n*['p'] # state labeling
        >>> ts1 = line_labeled_with(L, n-1)
        >>> ts1.plot()
        >>> 
        >>> L = n*['p']
        >>> ts2 = cycle_labeled_with(L)
        >>> ts2.states.label('s3', '!p')
        >>> ts2.plot()
        >>> 
        >>> ts3 = ts1 +ts2
        >>> ts3.transitions.add('s'+str(n-1), 's'+str(n) )
        >>> ts3.default_layout = 'circo'
        >>> ts3.plot()
        
        see also
        --------
        line_labeled_with, cycle_labeled_with
        
        @param other: system to merge with
        @type other: C{FiniteTransitionSystem}
        
        @return: merge of C{self} with C{other}, union of states, initial states,
            atomic propositions, actions, edges and labelings, with those
            of C{other} taking precedence over C{self}.
        @rtype: FiniteTransitionSystem
        """
        if not isinstance(other, FiniteTransitionSystem):
            raise TypeError('other class must be FiniteTransitionSystem.\n' +
                            'Got instead:\n\t' +str(other) +
                            '\nof type:\n\t' +str(type(other) ) )
        
        self.atomic_propositions |= other.atomic_propositions
        self.actions |= other.actions
        
        # add extra states & their labels
        for state, label in other.states.find():
            if state not in self.states:
                self.states.add(state)
            
            if label:
                self.states.label(state, label['ap'] )
        
        self.states.initial |= other.states.initial()
        
        # copy extra transitions (be careful w/ labeling)
        for (from_state, to_state, label_dict) in other.transitions.find():
            # labeled edge ?
            if not label_dict:
                self.transitions.add(from_state, to_state)
            else:
                sublabel_value = label_dict['actions']
                self.transitions.add_labeled(from_state, to_state, sublabel_value)
        
        return copy.copy(self)
    
    def __or__(self, ts):
        """Synchronous product between transition systems."""
        return self.async_prod(ts)
    
    def sync_prod(self, ts_or_ba):
        """Synchronous product TS x BA or TS1 x TS2.
        
        see also
        --------
        __mul__, async_prod, BuchiAutomaton.sync_prod, tensor_product
        Def. 2.42, pp. 75--76 [Baier 2008]
        Def. 4.62, p.200 [Baier 2008]
        """
        if isinstance(ts_or_ba, FiniteTransitionSystem):
            ts = ts_or_ba
            return self._sync_prod(ts)
        elif isinstance(ts_or_ba, automata.BuchiAutomaton):
            ba = ts_or_ba
            return automata._ts_ba_sync_prod(self, ba)
        else:
            raise Exception('Argument must be TS or BA.')
    
    def _sync_prod(self, ts):
        """Synchronous (tensor) product with other FTS.
        
        @param ts: other FTS with which to take synchronous product
        @type ts: FiniteTransitionSystem
        """
        # type check done by caller: sync_prod
        if self.states.mutants or ts.states.mutants:
            mutable = True
        else:
            mutable = False
        
        prod_ts = FiniteTransitionSystem(mutable=mutable)
        
        # union of AP sets
        prod_ts.atomic_propositions |= \
            self.atomic_propositions | ts.atomic_propositions
        
        # for synchronous product: Cartesian product of action sets
        prod_ts.actions |= self.actions * ts.actions
        
        prod_ts = super(FiniteTransitionSystem, self).tensor_product(
            ts, prod_sys=prod_ts
        )
        
        return prod_ts
    
    def async_prod(self, ts):
        """Asynchronous product TS1 x TS2 between FT Systems.
        
        see also
        --------
        __or__, sync_prod, cartesian_product
        Def. 2.18, p.38 [Baier 2008]
        """
        if not isinstance(ts, FiniteTransitionSystem):
            raise TypeError('ts must be a FiniteTransitionSystem.')
        
        if self.states.mutants or ts.states.mutants:
            mutable = True
        else:
            mutable = False
        
        # union of AP sets
        prod_ts = FiniteTransitionSystem(mutable=mutable)
        prod_ts.atomic_propositions |= \
            self.atomic_propositions | ts.atomic_propositions
        
        # for parallel product: union of action sets
        prod_ts.actions |= self.actions | ts.actions
        
        prod_ts = super(FiniteTransitionSystem, self).cartesian_product(
            ts, prod_sys=prod_ts
        )
        
        return prod_ts

    # operations between transition systems    
    def intersection(self):
        """Conjunct with another FTS.
        """
        raise NotImplementedError
        
    def difference(self):
        """Remove a sub-FTS.
        """
        raise NotImplementedError

    def composition(self):
        """Compositions of FTS, with state replaced by another FTS.
        """
        raise NotImplementedError
    
    def project(self, factor=None):
        """Project onto subgraph or factor graph.
        
        @param factor: on what to project:
            - If C{None}, then project on subgraph, i.e., using states
            - If C{int}, then project on the designated element of
                the tuple comprising each state
        @type factor: None | int
        """
        raise NotImplementedError
    
    def simulate(self, state_sequence="random"):
        """Simulate Finite Transition System.
        
        @type state_sequence: inputs="random"
            | given array
        
        see also
        --------
        is_simulation
        """
        raise NotImplementedError
    
    def sim(self, **args):
        """Alias to simulate.
        """
        return self.simulate(**args)
    
    def is_simulation(self, simulation=FTSSim() ):
        """Check path, execution, trace or simulation given.
        
        terminology
        -----------
        - A path is a sequence of states.
        - An execution is a sequence of alternating states, actions.
        - A trace is the lift of a path by the labeling.
            (Caution: a single trace may project on multiple paths)
        - A bundle of the above is here called a simulation.
        
        see also
        --------
        simulate
        """
        raise NotImplementedError
    
    def loadSPINAut():
        raise NotImplementedError
    
    def promela_str(self, procname=None):
        """Convert an automaton to Promela source code.
        
        Creats a process which can be simulated as an independent
        thread in the SPIN model checker.
        
        see also
        --------
        save, plot
        
        @param fname: file name
        @type fname: str
        
        @param procname: Promela process name, i.e., proctype procname())
        @type procname: str (default: system's name)
        
        @param add_missing_extension: add file extension 'pml', if missing
        @type add_missing_extension: bool
        """
        def state2promela(state, ap_label, ap_alphabet):
            s = str(state) +':\n'
            s += '\t printf("State: ' +str(state) +'\\n");\n\t atomic{'
            
            # convention ! means negation
            
            missing_props = filter(lambda x: x[0] == '!', ap_label)
            present_props = ap_label.difference(missing_props)
            
            assign_props = lambda x: str(x) + ' = 1;'
            if present_props:
                s += ' '.join(map(assign_props, present_props) )
            
            # rm "!"
            assign_props = lambda x: str(x[1:] ) + ' = 0;'
            if missing_props:
                s += ' '.join(map(assign_props, missing_props) )
            
            s += '}\n'
            return s
        
        def outgoing_trans2promela(transitions):
            s = '\t if\n'
            for (from_state, to_state, sublabels_dict) in transitions:
                s += '\t :: printf("' +str(sublabels_dict) +'\\n");\n'
                s += '\t\t goto ' +str(to_state) +'\n'
            s += '\t fi;\n\n'
            return s
        
        if procname is None:
            procname = self.name
        
        s = ''
        for ap in self.atomic_propositions:
            # convention "!" means negation
            if ap[0] != '!':
                s += 'bool ' +str(ap) +';\n'
        
        s += '\nactive proctype ' +procname +'(){\n'
        
        s += '\t if\n'
        for initial_state in self.states.initial:
            s += '\t :: goto ' +str(initial_state) +'\n'
        s += '\t fi;\n'
        
        for state in self.states():
            ap_alphabet = self.atomic_propositions
            ap_label = self.states.label_of(state)
            s += state2promela(state, ap_label, ap_alphabet)
            
            outgoing_transitions = self.transitions.find({state}, as_dict=True)
            s += outgoing_trans2promela(outgoing_transitions)
        
        s += '}\n'
        return s
    
    def save_promela(self, fname=None, add_missing_extension=True):
        if fname is None:
            fname = self.name
            fname = self._export_fname(fname, 'pml', add_missing_extension)
        
        s = '/*\n * Promela file generated with TuLiP\n'
        s += ' * Data: '+str(strftime('%x %X %z') ) +'\n */\n\n'
        
        s += self.promela_str()
        
        # dump to file
        f = open(fname, 'w')
        f.write(s)
        f.close()

class FTS(FiniteTransitionSystem):
    """Alias to FiniteTransitionSystem."""
    
    def __init__(self, *args, **kwargs):
        FiniteTransitionSystem.__init__(self, *args, **kwargs)

class OpenFiniteTransitionSystem(LabeledStateDiGraph):
    """Analogous to FTS, but for open systems, with system and environment."""
    def __init__(self, atomic_propositions=[], sys_actions=[],
                 env_actions=[], **args):
        # state labeling
        self._state_label_def = OrderedDict(
            [['ap', PowerSet(atomic_propositions) ]]
        )
        self.atomic_propositions = self._state_label_def['ap'].math_set
        self._state_dot_label_format = {'ap':'',
                                           'type?label':'',
                                           'separator':'\\n'}
        
        # edge labeling (here 2 sublabels)
        self._transition_label_def = OrderedDict([
            ['sys_actions', MathSet(sys_actions) ],
            ['env_actions', MathSet(env_actions) ]
        ])
        self.sys_actions = self._transition_label_def['sys_actions']
        self.env_actions = self._transition_label_def['env_actions']
        self._transition_dot_label_format = {'sys_actions':'sys',
                                                'env_actions':'env',
                                                'type?label':':',
                                                'separator':'\\n'}
        
        LabeledStateDiGraph.__init__(self, **args)
        
        self.dot_node_shape = {'normal':'box'}
        self.default_export_fname = 'ofts'
        
    def __repr__(self):
        s = hl +'\nFinite Transition System (open) : '
        s += self.name +'\n' +hl +'\n'
        s += 'Atomic Propositions:\n'
        s += pformat(self.atomic_propositions, indent=3) +2*'\n'
        s += 'States & State Labels (\in 2^AP):\n'
        s += pformat(self.states(data=True), indent=3) +2*'\n'
        s += 'Initial States:\n'
        s += pformat(self.states.initial, indent=3) +2*'\n'
        s += 'System Actions:\n' +pformat(self.sys_actions, indent=3) +2*'\n'
        s += 'Environment Actions:\n' +pformat(self.env_actions, indent=3) +2*'\n'
        s += 'Transitions & Labeling w/ Sys, Env Actions:\n'
        s += pformat(self.transitions(labeled=True), indent=3) +'\n' +hl +'\n'
        
        return s
    
    def __str__(self):
        return self.__repr__()

class OpenFTS(OpenFiniteTransitionSystem):
    """Alias to transys.OpenFiniteTransitionSystem."""
    def __init__(self, **args):
        OpenFiniteTransitionSystem.__init__(self, **args)

def negation_closure(atomic_propositions):
    """Given: ['p', ...], return: [True, 'p', '!p', ...].
    
    @param atomic_propositions: AP set
    @type atomic_propositions: iterable container of strings
    """
    def negate(x):
        # starts with ! ?
        if x.find('!') == 0:
            x = x[1:]
        else:
            x = '!'+x
        return x
    
    if not isinstance(atomic_propositions, Iterable):
        raise TypeError('atomic_propositions must be Iterable.'
                        'Got:\n\t' +str(atomic_propositions) +'\ninstead.')
    
    ap = [f(x)
          for x in atomic_propositions
          for f in (lambda x: x, negate) ] +[True]
    return unique(ap)

def tuple2fts(S, S0, AP, L, Act, trans, name='fts',
              prepend_str=None, verbose=False):
    """Create a Finite Transition System from a tuple of fields.

    hint
    ====
    To rememeber the arg order:

    1) it starts with states (S0 requires S before it is defined)

    2) continues with the pair (AP, L), because states are more fundamental
    than transitions (transitions require states to be defined)
    and because the state labeling L requires AP to be defined.

    3) ends with the pair (Act, trans), because transitions in trans require
    actions in Act to be defined.

    see also
    ========
    L{tuple2ba}

    @param S: set of states
    @type S: iterable of hashables
    
    @param S_0: set of initial states, must be \\subset S
    @type S_0: iterable of elements from S
    
    @param AP: set of Atomic Propositions for state labeling:
            L: S-> 2^AP
    @type AP: iterable of hashables
    
    @param L: state labeling definition
    @type L: iterable of (state, AP_label) pairs:
        [(state0, {'p'} ), ...]
        | None, to skip state labeling.
    
    @param Act: set of Actions for edge labeling:
            R: E-> Act
    @type Act: iterable of hashables
    
    @param trans: transition relation
    @type trans: list of triples: [(from_state, to_state, act), ...] where act \\in Act
    
    @param name: used for file export
    @type name: str
    """
    def pair_labels_with_states(states, state_labeling):
        if state_labeling is None:
            return
        
        if not isinstance(state_labeling, Iterable):
            raise TypeError('State labeling function: L->2^AP must be '
                            'defined using an Iterable.')
        
        state_label_pairs = True
        
        # cannot be caught by try below
        if isinstance(state_labeling[0], str):
            state_label_pairs = False
        
        try:
            (state, ap_label) = state_labeling[0]
        except ValueError:
            state_label_pairs = False
        
        if state_label_pairs:
            return state_labeling
        
        vprint('State labeling L not tuples (state, ap_label),\n'
                   'zipping with states S...\n', verbose)
        state_labeling = zip(states, state_labeling)
        return state_labeling
    
    # args
    if not isinstance(S, Iterable):
        raise TypeError('States S must be iterable, even for single state.')
    
    # convention
    if not isinstance(S0, Iterable) or isinstance(S0, str):
        S0 = [S0]
    
    # comprehensive names
    states = S
    initial_states = S0
    ap = AP
    state_labeling = pair_labels_with_states(states, L)
    actions = Act
    transitions = trans
    
    # prepending states with given str
    if prepend_str:
        vprint('Given string:\n\t' +str(prepend_str) +'\n' +
               'will be prepended to all states.', verbose)
    states = prepend_with(states, prepend_str)
    initial_states = prepend_with(initial_states, prepend_str)
    
    ts = FTS(name=name)
    
    ts.states.add_from(states)
    ts.states.initial |= initial_states
    
    ts.atomic_propositions |= ap
    
    # note: verbosity before actions below
    # to avoid screening by possible error caused by action
    
    # state labeling assigned ?
    if state_labeling is not None:
        for (state, ap_label) in state_labeling:
            ap_label = str2singleton(ap_label, verbose=verbose)
            (state,) = prepend_with([state], prepend_str)
            
            vprint('Labeling state:\n\t' +str(state) +'\n' +
                  'with label:\n\t' +str(ap_label) +'\n', verbose)
            ts.states.label(state, ap_label)
    
    # any transition labeling ?
    if actions is None:
        for (from_state, to_state) in transitions:
            (from_state, to_state) = prepend_with([from_state, to_state],
                                                  prepend_str)
            vprint('Added unlabeled edge:\n\t' +str(from_state) +
                   '--->' +str(to_state) +'\n', verbose)
            ts.transitions.add(from_state, to_state)
    else:
        ts.actions |= actions
        for (from_state, to_state, act) in transitions:
            (from_state, to_state) = prepend_with([from_state, to_state],
                                                  prepend_str)
            vprint('Added labeled edge (=transition):\n\t' +
                   str(from_state) +'---[' +str(act) +']--->' +
                   str(to_state) +'\n', verbose)
            ts.transitions.add_labeled(from_state, to_state, act)
    
    return ts

def line_labeled_with(L, m=0):
    """Return linear FTS with given labeling.
    
    The resulting system will be a terminating sequence:
        s0-> s1-> ... -> sN
    where: N = C{len(L) -1}.
    
    see also
    --------
    cycle_labeled_with
    
    @param L: state labeling
    @type L: iterable of state labels, e.g., [{'p', '!p', 'q',...]
        Single strings are identified with singleton Atomic Propositions,
        so [..., 'p',...] and [...,{'p'},...] are equivalent.
    
    @param m: starting index
    @type m: int
    
    @return: FTS with:
        - states ['s0', ..., 'sN'], where N = len(L) -1
        - state labels defined by L, so s0 is labeled with L[0], etc.
        - transitions forming a sequence:
            - s_{i} ---> s_{i+1}, for: 0 <= i < N
    """
    n = len(L)
    S = range(m, m+n)
    S0 = [] # user will define them
    AP = negation_closure(L)
    Act = None
    from_states = range(m, m+n-1)
    to_states = range(m+1, m+n)
    trans = zip(from_states, to_states)
    
    ts = tuple2fts(S, S0, AP, L, Act, trans, prepend_str='s')
    return ts

def cycle_labeled_with(L):
    """Return cycle FTS with given labeling.
    
    The resulting system will be a cycle:
        s0-> s1-> ... -> sN -> s0
    where: N = C{len(L) -1}.
    
    see also
    --------
    line_labeled_with
    
    @param L: state labeling
    @type L: iterable of state labels, e.g., [{'p', 'q'}, ...]
        Single strings are identified with singleton Atomic Propositions,
        so [..., 'p',...] and [...,{'p'},...] are equivalent.
    
    @return: FTS with:
        - states ['s0', ..., 'sN'], where N = len(L) -1
        - state labels defined by L, so s0 is labeled with L[0], etc.
        - transitions forming a cycle:
            - s_{i} ---> s_{i+1}, for: 0 <= i < N
            - s_N ---> s_0
    """
    ts = line_labeled_with(L)
    last_state = 's' +str(len(L)-1)
    ts.transitions.add(last_state, 's0')
    
    #trans += [(n-1, 0)] # close cycle
    return ts