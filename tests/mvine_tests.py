from unittest import TestCase
try:
  from unittest.mock import MagicMock as Mock
except ImportError as e:
  from mock import Mock

from skypyblue.models import *
from skypyblue.core import Mvine, Marker, ConstraintSystem

marker = Marker()
new_mark = marker.new_mark

class MVineTests(TestCase):

  def setUp(self):
    self.marker = marker
    self.mvine = Mvine(self.marker)
    self.cs = ConstraintSystem()

  def test_build_mvine(self):
    v1, v2, v3 = self.cs.create_variables(["v1", "v2", "v3"], [3, 4, 5])

    m1 = Method([v1, v2], [v3], lambda v1, v2: (v1 + v2) / 2)

    m2 = Method([v3, v2], [v1], lambda v3, v2: 2 * v3 - v2)

    m3 = Method([v3, v1], [v2], lambda v3, v1: 2 * v3 - v1)
    cn = Constraint(
        lambda v1, v2, v3: True,
        Strength.STRONG,
        [v1, v2, v3],
        [m1, m2, m3])

    self.assertIsNone(v1.determined_by)
    self.assertIsNone(v2.determined_by)
    self.assertIsNone(v3.determined_by)

    self.assertEqual(3, v1.get_value())
    self.assertEqual(4, v2.get_value())
    self.assertEqual(5, v3.get_value())

    redetermined_vars = set()
    self.assertTrue(self.mvine.build(cn, redetermined_vars))

    self.assertEqual(set([v3]), redetermined_vars)
    self.assertIsNone(v1.determined_by)
    self.assertIsNone(v2.determined_by)
    self.assertEqual(cn, v3.determined_by)
    self.assertIsNotNone(cn.mark)

