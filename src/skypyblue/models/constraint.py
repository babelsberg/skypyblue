
class Constraint:
  def __init__(self, check_function, strength, variables, methods):
    """
    check_function:  \tis lambda returning bool. defines a contraint and can be used to check, whether the contraint is fullfilled
    strength:   \tis of type skypyblue.models.strength.Strength and indicates how important it is to fullfill the contraint
    variables:   \tlist of skypyblue.models.variables.Variable that are involved in the contraint
    methods:    \tlist of skypyblue.models.methods.Method that can fullfill a contraint
    """
    self.check_function = check_function
    self.strength = strength
    self.variables = variables
    self.methods = methods

    self.selected_method = None
    self.mark = None

  def is_enforced(self):
    "returns True is there is is a method selected, otherwise False"
    return not self.selected_method is None
