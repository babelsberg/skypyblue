import inspect
class Constraint:
  def __init__(self, check_function, strength, variables, methods):
    """
    check_function: is lambda returning bool. defines a contraint and can be used to check, whether the contraint is fullfilled
    strength:       is of type skypyblue.models.strength.Strength and indicates how important it is to fullfill the contraint
    variables:      list of skypyblue.models.variables.Variable that are involved in the contraint
    methods:        list of skypyblue.models.methods.Method that can fullfill a contraint

    Usage:
      c = Constraint(
        lambda v1, v2: v1 < v2,
        Strength.STRONG,
        [v1, v2],
        [some_method])
    """
    self.check_function = check_function
    self.strength = strength
    self.variables = variables if isinstance(variables, list) else [variables]
    self.methods = methods if isinstance(methods, list) else [methods]

    self.selected_method = None
    self.mark = None

  def add_to_pplan(self, pplan, done_mark):
    if self.is_enforced() and self.mark != done_mark:
      self.mark = done_mark
      for var in self.selected_method.outputs:
        pplan.extend(var.add_to_pplan(pplan, done_mark))
      pplan.append(self)
    return pplan

  def is_enforced(self):
    "returns True is there is is a method selected, otherwise False"
    return not self.selected_method is None

  def __str__(self):
    return "<Constraint check: %s>" % (
      inspect.getsource(self.check_function).strip())

  def __repr__(self):
    return str(self)

