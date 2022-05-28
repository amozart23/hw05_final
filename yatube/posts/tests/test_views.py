import shutil
import tempfile
from posts.models import Post, Group, Comment

from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Anonymous')
        cls.client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Пробная группа',
            slug='test-slug',
            description='Описание группы',
        )

        cls.group2 = Group.objects.create(
            title='Вторая группа',
            slug='test-slug2',
            description='Описание пробной группы',
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.post = Post.objects.create(
            text='Просто какой-то текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=cls.post,
            author=cls.user,
        )
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_use_correct_templates(self):
        """Все страницы используют правильные шаблоны."""
        post = PostViewsTests.post
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': post.id}):
            'posts/create_post.html',
            reverse('posts:group_posts', kwargs={'slug': 'test-slug'}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'Anonymous'}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': post.id}):
            'posts/post_detail.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def returning_first_object_field(self, response, field):
        object = response.context['page_obj'][0]
        return getattr(object, field)

    def test_home_page_shows_correct_context(self):
        """Главная страница выдает правильный контекст."""
        response = self.authorized_client.get(reverse('posts:index'))
        author = PostViewsTests.user
        image = PostViewsTests.post.image
        self.assertEqual(self.returning_first_object_field(response, 'text'),
                         'Просто какой-то текст')
        self.assertEqual(self.returning_first_object_field(response, 'author'),
                         author)
        self.assertEqual(self.returning_first_object_field(response, 'image'),
                         image)

    def test_group_page_shows_correct_context(self):
        """Страница группы выдает правильный контекст."""
        response = self.client.get(reverse
                                   ('posts:group_posts', kwargs={'slug':
                                                                 'test-slug'}))
        author = PostViewsTests.user
        group = PostViewsTests.group
        image = PostViewsTests.post.image
        self.assertEqual(self.returning_first_object_field(response, 'text'),
                         'Просто какой-то текст')
        self.assertEqual(self.returning_first_object_field(response, 'author'),
                         author)
        self.assertEqual(self.returning_first_object_field(response, 'group'),
                         group)
        self.assertEqual(self.returning_first_object_field(response, 'image'),
                         image)
        self.assertEqual(response.context['group'], group)

    def test_user_page_shows_correct_context(self):
        """Страница профиля пользователя выдает правильный контекст."""
        response = self.client.get(reverse
                                   ('posts:profile', kwargs={'username':
                                                             'Anonymous'}))
        author = PostViewsTests.user
        group = PostViewsTests.group
        image = PostViewsTests.post.image
        self.assertEqual(self.returning_first_object_field(response, 'text'),
                         'Просто какой-то текст')
        self.assertEqual(self.returning_first_object_field(
            response, 'author'), author)
        self.assertEqual(self.returning_first_object_field(response, 'group'),
                         group)
        self.assertEqual(self.returning_first_object_field(response, 'image'),
                         image)
        self.assertEqual(response.context['post_count'], 1)
        self.assertEqual(response.context['author'], author)

    def test_post_detail_page_shows_correct_context(self):
        """Страница с деталями поста выдает ожидаемый контекст."""
        post = PostViewsTests.post
        author = PostViewsTests.user
        image = PostViewsTests.post.image
        response = (self.client.get(reverse('posts:post_detail',
                    kwargs={'post_id': post.id})))
        self.assertEqual(response.context.get(
            'current_post').text, 'Просто какой-то текст')
        self.assertEqual(response.context.get(
            'current_post').image, image)
        self.assertEqual(response.context.get('current_post').author, author)
        self.assertEqual(response.context['comments'][0],
                         PostViewsTests.comment)

    def test_task_detail_pages_show_correct_context(self):
        """Страница редактирования поста выдает форму для нужного поста."""
        post = PostViewsTests.post
        response = (self.authorized_client.get(reverse('posts:post_edit',
                    kwargs={'post_id': post.id})))
        self.assertEqual(response.context.get(
            'post').id, post.id)

    def test_create_post_page_shows_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.models.ModelChoiceField,
            'text': forms.fields.CharField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_one_post_shows_everywhere(self):
        """Пост появляется везде где должен."""
        lenght_group2 = len(Post.objects.filter(group__slug='test-slug2'))
        self.assertEqual(lenght_group2, 0)
        lenght_group = len(Post.objects.filter(group__slug='test-slug'))
        self.assertEqual(lenght_group, 1)
        response = self.client.get(reverse('posts:group_posts',
                                           kwargs={'slug': 'test-slug2'}))
        alternative_group_is_not_empty = response.context['page_obj']
        self.assertFalse(alternative_group_is_not_empty)
        response = self.client.get(reverse('posts:index'))
        cheking_object_homepage = response.context['page_obj'][0]
        response = self.client.get(reverse
                                   ('posts:profile', kwargs={'username':
                                                             'Anonymous'}))
        cheking_object_profile = response.context['page_obj'][0]
        response = self.client.get(reverse('posts:group_posts',
                                           kwargs={'slug': 'test-slug'}))
        cheking_object_group_list = response.context['page_obj'][0]
        self.assertEqual(cheking_object_homepage.text, 'Просто какой-то текст')
        self.assertEqual(cheking_object_profile.text, 'Просто какой-то текст')
        self.assertEqual(cheking_object_group_list.text,
                         'Просто какой-то текст')

    def test_cache(self):
        """Посты на главной кэшируются."""
        post = Post.objects.create(
            text='Кэшированный пост',
            author=self.user,
        )
        response = self.client.get(reverse('posts:index'))
        post.delete()
        self.assertContains(response, post.text)
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        self.assertNotContains(response, post.text)


class PaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Anonymous')
        cls.client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Пробная группа',
            slug='test-slug',
            description='Описание группы',
        )

        Post.objects.bulk_create(
            [Post(text=i,
                  author=cls.user, group=cls.group) for i in range(13)])

    def test_paginators(self):
        """Тестирование пажинаторов."""
        quantity_of_objects_on_the_page = {
            reverse('posts:index'): 10,
            reverse('posts:index') + '?page=2': 3,
            reverse('posts:group_posts', kwargs={'slug': 'test-slug'}): 10,
            reverse('posts:group_posts', kwargs={
                'slug': 'test-slug'}) + '?page=2': 3,
            reverse('posts:profile', kwargs={'username': 'Anonymous'}): 10,
            reverse('posts:profile', kwargs={
                'username': 'Anonymous'}) + '?page=2': 3}

        for address, expected in quantity_of_objects_on_the_page.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(len(response.context['page_obj']), expected)

