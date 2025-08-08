# Tests for accounts app
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserTestCase(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

    def test_user_creation(self):
        self.assertEqual(self.student.role, 'student')
        self.assertEqual(self.teacher.role, 'teacher')
        self.assertTrue(self.student.is_student())
        self.assertTrue(self.teacher.is_teacher())

    def test_user_str_representation(self):
        self.assertEqual(str(self.student), 'student1 (student)')
        self.assertEqual(str(self.teacher), 'teacher1 (teacher)')
