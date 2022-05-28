from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='Anonymous')
        cls.user2 = User.objects.create_user(username='Hacker')
        cls.another_authorized_client = Client()
        cls.another_authorized_client.force_login(cls.user2)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Пробная группа',
            slug='test-slug',
            description='Описание группы',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )

    def test_pages_urls_codes_from_unathorized_user(self):
        """На запросы возвращаются корректные HTTP-статусы состояния."""
        post_id = str(PostURLTests.post.id)
        username = PostURLTests.user.username
        group_slug = PostURLTests.group.slug

        unexisting_page_url = '/unexisting-page/'
        main_page_url = '/'
        group_url = '/group/' + group_slug + '/'
        profile_url = '/profile/' + username + '/'
        post_url = '/posts/' + post_id + '/'
        create_post_url = '/create/'
        edit_post_url = '/posts/' + post_id + '/edit/'
        add_comment_url = '/posts/' + post_id + '/comment/'

        urls_dict = {
            unexisting_page_url: 'Not Found',
            main_page_url: 'OK',
            group_url: 'OK',
            profile_url: 'OK',
            post_url: 'OK',
            create_post_url: 'Found',
            edit_post_url: 'Found',
            add_comment_url: 'Found',
        }
        for address, expected_phrase in urls_dict.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.reason_phrase, expected_phrase)

    def test_post_edit_is_available_for_the_author(self):
        """Авторизованному пользователю - автору поста доступно его
        редактирование.
        """
        post_id = str(PostURLTests.post.id)
        response = self.authorized_client.get('/posts/' + post_id + '/edit/')
        self.assertEqual(response.reason_phrase, 'OK')

    def test_create_post_url_exists_at_desired_location(self):
        """Авторизованному пользователю доступно создание поста."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.reason_phrase, 'OK')

    def test_add_comment_url_exists_at_desired_location(self):
        """Авторизованному пользователю доступно написание коммента."""
        post_id = str(PostURLTests.post.id)
        response = self.authorized_client.get(
            '/posts/' + post_id + '/comment/')
        self.assertEqual(response.reason_phrase, 'Found')
        self.assertRedirects(response, '/posts/' + post_id + '/')

    def test_post_edit_redirects_for_nonauthor_user(self):
        """Авторизованному пользователю - не-автору поста недоступно его
        редактирование, происходит редирект.
        """
        post_id = str(PostURLTests.post.id)
        response = self.another_authorized_client.get(
            '/posts/' + post_id + '/edit/')
        self.assertEqual(response.reason_phrase, 'Found')

    def test_all_urls_correct_templates(self):
        """Все url используют правильные шаблоны."""

        post_id = str(PostURLTests.post.id)
        username = PostURLTests.user.username
        group_slug = PostURLTests.group.slug

        main_page_url = '/'
        group_url = '/group/' + group_slug + '/'
        profile_url = '/profile/' + username + '/'
        post_url = '/posts/' + post_id + '/'
        create_post_url = '/create/'
        edit_post_url = '/posts/' + post_id + '/edit/'

        templates_url_names = {
            main_page_url: 'posts/index.html',
            group_url: 'posts/group_list.html',
            profile_url: 'posts/profile.html',
            post_url: 'posts/post_detail.html',
            create_post_url: 'posts/create_post.html',
            edit_post_url: 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
