from unittest import TestCase
try:
  from unittest.mock import MagicMock as Mock
except ImportError as e:
  from mock import Mock

from skypyblue.constraint_system import ConstraintSystem, max_out
from skypyblue.models import *

new_mark = ConstraintSystem().new_mark

class MVineTests(TestCase):
  
  def setUp(self):
    self.cs = ConstraintSystem()

  def test_mvine_revoke_cn_fails(self):
    self.cs.mvine_grow = Mock(return_value = False)
    cn = Constraint(None, Strength.WEAKEST, [], [])
    cn.mark = new_mark()

    not_revoked = self.cs.mvine_revoke_cn(cn, Strength.WEAKEST, new_mark(), [], [])
    
    self.assertFalse(not_revoked)
    self.assertTrue(cn.mark is None)

  def test_mvine_revoke_cn_succeeds(self):
    self.cs.mvine_grow = Mock(return_value = True)


    cn = Constraint(None, Strength.WEAKEST, [], [])
    v1 = self.cs.create_variable("v1", 1)
    v2 = self.cs.create_variable("v2", 2)
    v3 = self.cs.create_variable("v3", 3)
    for v in [v1,v2,v3]: v.walk_strength = Strength.WEAK

    m = Method([v1, v2], v3, None)
    cn.selected_method = m
    v3.determined_by = m
    redetermined_vars = []

    not_revoked = self.cs.mvine_revoke_cn(cn, Strength.WEAKEST, new_mark(), [], redetermined_vars)
    
    self.assertTrue (not_revoked)
    self.assertEqual(Strength.WEAK, v1.walk_strength)
    self.assertEqual(Strength.WEAK, v2.walk_strength)
    self.assertEqual(Strength.WEAKEST, v3.walk_strength)
    self.assertTrue (v3.determined_by is None)
    self.assertTrue (v3 in redetermined_vars)
    self.assertTrue (cn.selected_method is None)

    # case 2 - v3's mark is the same as passed to mvine_revoke_cn
    
    mark = new_mark()
    cn.selected_method = m
    v3.walk_strength = Strength.WEAK
    v3.determined_by = m
    v3.mark = mark
    redetermined_vars = []
    not_revoked = self.cs.mvine_revoke_cn(cn, Strength.WEAKEST, mark, [], redetermined_vars)

    self.assertTrue (not_revoked)
    self.assertEqual(Strength.WEAK, v1.walk_strength)
    self.assertEqual(Strength.WEAK, v2.walk_strength)
    self.assertEqual(Strength.WEAK, v3.walk_strength)
    self.assertTrue (v3.determined_by is m)
    self.assertTrue (v3 not in redetermined_vars)
    self.assertTrue (cn.selected_method is None)    

  # mvine_revoke_cn(cn, Strength.WEAKEST, new_mark(), [], [])
  def test_mvine_grow_with_empty_stack(self):
    self.assertTrue(self.cs.mvine_grow(Strength.WEAKEST, new_mark(), [], []))

  def test_mvine_grow_with_marked_constraints(self):
    mark = new_mark()
    cn1 = Constraint(None, Strength.WEAKEST, [], [])
    cn2 = Constraint(None, Strength.WEAKEST, [], [])
    cn1.mark = mark
    # self.assertTrue(mvine_grow(Strength.WEAKEST, mark, [cn1, cn2], []))

  def test_mvine_grow_with_unmarked_and_weak_constraints(self):
    mark = new_mark()
    cn1 = Constraint(None, Strength.WEAKEST, [], [])
    cn2 = Constraint(None, Strength.WEAKEST, [], [])
    self.cs.mvine_revoke_cn = Mock(return_value = True)
    self.cs.mvine_revoke_cn = Mock(return_value = False)
    stack = [cn2, cn1]
    self.assertFalse(self.cs.mvine_grow(Strength.MEDIUM, mark, stack, []))

  def test_mvine_grow_with_(self):
    mark = new_mark()
    cn1 = Constraint(None, Strength.WEAKEST, [], [])
    cn2 = Constraint(None, Strength.REQUIRED, [], [])
    cn1.mark = mark
    self.cs.mvine_enforce_cn = Mock(return_value = False)
    stack = [cn2, cn1]
    self.assertFalse(self.cs.mvine_grow(Strength.MEDIUM, mark, stack, []))
    

  def test_mvine_enforce_cn_with_no_methods_fails(self):
    cn = Constraint(None, Strength.WEAKEST, [], [])
    cn.mark = new_mark()
    self.cs.possible_method = Mock(return_value = False)

    self.assertFalse(self.cs.mvine_enforce_cn(cn, Strength.WEAKEST, new_mark(), [], []))
    self.assertTrue(cn.mark is None)

  def test_mvine_enforce_cn_fails(self):
    v1 = Variable("v1", 1)
    v2 = Variable("v2", 2)
    v3 = Variable("v3", 3)
    m = Method([v1, v2], v3, None)
    cn = Constraint(None, Strength.WEAKEST, [], m)
    cn.mark = new_mark()
    self.cs.possible_method = Mock(return_value = False)

    self.assertFalse(self.cs.mvine_enforce_cn(cn, Strength.WEAKEST, new_mark(), [], []))
    self.assertTrue(cn.mark is None)


  # a valid constraint system should not contain method conflicts
  def check_constraint_system(self, constraint_system):
    constrained_variables = set()
    for constraint in constraint_system.constraints:
      if not constraint.is_enforced:
        continue
      for out_var in constraint.selected_method.out_vars:
        if out_var in constrained_variables:
          return False
        constrained_variables.add(out_var)
    return True