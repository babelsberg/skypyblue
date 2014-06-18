from skypyblue.models import Variable, Method, Constraint, Strength, InternalStrength
from skypyblue.core import Mvine, Marker
import pdb;
class ConstraintSystem:

  def __init__(self):
    self.marker = Marker()
    self.constraints = []
    self.variables = []
    self.forced_constraint = None
    self.check_constraints = True

  def create_variables(self, names, initialValues):
    assert len(names) == len(initialValues)
    res = []
    for i in range(len(names)):
      res.append(self.create_variable(names[i], initialValues[i]))
    return res

  # TODO: Remove these
  def create_variable(self, name, initialValue):
    variable = Variable(name, initialValue, self)
    self.variables.append(variable)
    return variable

  def change_variable_values(self, variables, values):
    if len(variables) == 1:
      values = values[0]

    m = Method([], variables,
      lambda: values)

    cn = Constraint(
      lambda x: True,
      InternalStrength.FORCED,
      variables,
      [m])

    if self.forced_constraint is not None:
      self.remove_constraint(self.forced_constraint, skip = True)

    self.forced_constraint = cn
    self.add_constraint(cn)

  def variable_changed(self, var):
    self.change_variable_values([var], [var.get_value()])

  def _check_constraints(self):
    if self.check_constraints == False:
      return
    for constraint in self.constraints:
      if not constraint.is_enforced():
        continue
      check = constraint.check_function(*[var.get_value() for var in constraint.variables])
      if not check:
        raise Exception("Constraint %s is not satisfied" % constraint)

  def add_stay_constraint(self, variable, strength):
    m = Method([], [variable], lambda: variable.get_value())
    stay_constraint = Constraint(
      lambda x: True,
      strength,
      [variable],
      [m])

    self.add_constraint(stay_constraint)
    return stay_constraint;

  def add_constraint(self, constraint):
    constraint.selected_method = None
    constraint.mark = None

    for variable in constraint.variables:
      variable.add_constraint(constraint)
    exec_roots = self.update_method_graph([constraint])
    self.exec_from_roots(exec_roots)

    self.constraints.append(constraint)
    self._check_constraints();

  def remove_constraint(self, constraint, skip = False):
    for variable in constraint.variables:
      variable.remove_constraint(constraint)

    self.constraints.remove(constraint)

    if constraint.is_enforced():
      old_outputs = constraint.selected_method.outputs
      constraint.selected_method = None

      exec_roots = []
      for variable in old_outputs:
        variable.determined_by = None
        variable.walk_strength = Strength.WEAKEST
        exec_roots.append(variable)

      if skip:
        return

      self.propagate_walk_strength(old_outputs)
      unenforcedConstraints = []
      self.collect_unenforced(unenforcedConstraints, old_outputs,constraint.strength,True)
      exec_roots.extend(self.update_method_graph(unenforcedConstraints))
      self.exec_from_roots(exec_roots)

    self._check_constraints();

  def update_method_graph(self, unenforced_constraints):
    exec_roots = []
    while unenforced_constraints:
      cn = self.strongest_constraint(unenforced_constraints)
      unenforced_constraints = [c for c in unenforced_constraints if c != cn]
      redetermined_vars = []
      if not Mvine(self.marker).build(cn, redetermined_vars):
        return exec_roots
      self.propagate_walk_strength([cn] + redetermined_vars)
      self.collect_unenforced(unenforced_constraints, redetermined_vars, cn.strength, False)
      exec_roots.append(cn)
      for var in redetermined_vars:
        if var.determined_by is None:
          exec_roots.append(var)
    return exec_roots

  def strongest_constraint(self, constraints):
    constraints.sort(key = lambda cn: cn.strength, reverse = True)
    return constraints[0]

  def weakest_constraint(self, constraints):
    constraints.sort(key=lambda cn: cn.strength)
    return constraints[0]

  def propagate_walk_strength(self, roots):
    self._new_mark()

    for cn in self.pplan_add(roots):
      if self.any_immediate_upstream_marked(cn):
        for var in cn.selected_method.inputs:
          if var.determined_by is not None and var.determined_by.mark == self.mark:
            var.walk_strength = Strength.WEAKEST
      self.compute_walkabout_strengths(cn)
      cn.mark = None

  def any_immediate_upstream_marked(self, cn):
    for var in cn.selected_method.inputs:
        if var.determined_by != None and var.determined_by.mark == self.mark:
          return True
    return False

  def compute_walkabout_strengths(self, cn):
    current_outputs = cn.selected_method.outputs
    for out_var in current_outputs:
      min_strength = cn.strength
      for mt in cn.methods:
        if not out_var in mt.outputs:
          max_strength = self.max_out(mt, current_outputs)
          if Strength.weaker(max_strength, min_strength):
            min_strength = max_strength
      out_var.walk_strength = min_strength

  def collect_unenforced(self, unenforced_cns, vars, collection_strength, collect_equal_strength):
    self._new_mark()
    for var in vars:
      collected = self.collect_unenforced_mark(unenforced_cns, var, collection_strength, collect_equal_strength)
      for val in set(collected):
        if val not in unenforced_cns:
          unenforced_cns.append(val)
    return unenforced_cns

  def collect_unenforced_mark(self, unenforced_cns, var, collection_strength, collect_equal_strength):
    for cn in var.constraints:
      if cn != var.determined_by and cn.mark != self.mark:
        cn.mark = self.mark
        if cn.is_enforced():
          for out_var in cn.selected_method.outputs:
            self.collect_unenforced_mark(unenforced_cns, out_var, collection_strength, collect_equal_strength)
        elif Strength.weaker(cn.strength, collection_strength) or \
              (collect_equal_strength and (cn.strength == collection_strength)):
          unenforced_cns.append(cn)
    return unenforced_cns


  def exec_pplan_create(self, exec_roots):
    exec_pplan = []

    for cn in exec_roots:
      if isinstance(cn, Constraint):
        cn.add_to_pplan(exec_pplan, self.mark)

    for var in exec_roots:
      if isinstance(var, Variable):
        if var.determined_by is None and not var.valid:
          exec_pplan.extend(var.add_to_pplan([], self.mark))
          var.valid = True

    return exec_pplan

  def exec_from_roots(self, exec_roots):
    self._new_mark()

    for cn in reversed(self.exec_pplan_create(exec_roots)):
      if cn.mark == self.mark:
        if self.any_immediate_upstream_marked(cn):
          self.exec_from_cycle(cn)
        else:
          cn.mark = None
          self.execute_propagate_valid(cn)

  def execute_propagate_valid(self, cn):
    inputs_valid = not cn.selected_method.has_invalid_vars()

    if inputs_valid:
      cn.selected_method.execute()

    for var in cn.selected_method.outputs:
      var.valid = inputs_valid

  def exec_from_cycle(self, cn):
    if cn.mark == self.mark:
      cn.mark = None
      for var in cn.selected_method.outputs:
        var.valid = False
        for consuming_cn in var.constraints:
          if consuming_cn != cn and consuming_cn.is_enforced:
            self.exec_from_cycle(consuming_cn)



  def pplan_add(self, objs):
    pplan = []
    if not isinstance(objs, list):
      raise Exception("accepting only list of objs!")
    for el in objs:
      el.add_to_pplan(pplan, self.mark)
    return pplan

  def _new_mark(self):
    self.marker.new_mark()

  @property
  def mark(self):
    return self.marker.mark

  # def extract_plan(self, root_cns):
  #   good_cns = []
  #   bad_cns = []
  #   self._new_mark()
  #   pplan = self.pplan_add([], root_cns)

  #   while pplan:
  #     cn = pplan.pop()
  #     if cn.mark != self.mark:
  #       pass
  #     elif self.any_immediate_upstream_marked(cn):
  #       bad_cns.append(cn)
  #     else:
  #       cn.mark = None
  #       good_cns.append(cn)
  #   return self.create_valid_plan(root_cns, good_cns, bad_cns)

  # def create_valid_plan(self, root_cns, good_cns, bad_cns):
  #   plan = Plan(root_cns, good_cns, bad_cns)
  #   for cns in [root_cns, good_cns, bad_cns]:
  #     for cn in cns:
  #       cn.valid_plans.append(plan)
  #   return plan

  # def invalidate_plans_on_setting_method(self, cn, new_mt):
  #   self.invalidate_constraint_plans(cl.valid_plans)
  #   if new_mt != None:
  #     for var in new_mt.inputs:
  #       if var.determined_by != None:
  #         self.invalidate_constraint_plans(var.determined_by)

  # def invalidate_constraint_plans(self, invalid_cn):
  #   for plan in invalid_cn.valid_plans:
  #     plan.valid = False
  #     for cns in [plan.good_cns, plan.bad_cns, plan.root_cns]:
  #       for cn in cns:
  #         if cn != invalid_cn:
  #           cn.valid_plans.remove(plan)
  #   invalid_cn.valid_plans.clear()

  # def execute_plan(self, plan):
  #   if plan.valid:
  #     for cn in plan.good_cns:
  #       self.execute_propagate_valid(cn)
  #   else:
  #     raise ValueError("trying to execute invalid plan")


  def max_out(self, mt, current_outputs):
    max_strength = Strength.WEAKEST
    for var in mt.outputs:
      if not var in current_outputs and \
        Strength.weaker(max_strength, var.walk_strength):
        max_strength = var.walk_strength
    return max_strength



