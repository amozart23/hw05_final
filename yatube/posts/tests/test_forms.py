import shutil
import tempfile

from django.conf import settings
from posts.forms import PostForm
from posts.models import Post, Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Anonymous')
        cls.group = Group.objects.create(title='test', slug='test_group')
        cls.group2 = Group.objects.create(title='test2', slug='test_group2')
        cls.post = Post.objects.create(
            text='Пост до редактирования',
            author=PostCreateFormTests.user,
            group=PostCreateFormTests.group,
        )
        cls.form = PostForm()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        username = PostCreateFormTests.user.username
        posts_count = Post.objects.count()
        group_of_the_post = PostCreateFormTests.group
        post_text = 'Тестовый текст'
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
        form_data = {
            'text': post_text,
            'group': group_of_the_post.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:profile', kwargs={'username':
                                                              username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(group_of_the_post.posts.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=post_text,
                group=group_of_the_post.id,
                author=PostCreateFormTests.user.id,
                image='posts/small.gif',
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма на странице редактирования изменяет пост."""
        new_text = 'Отредаченный пост'
        form_data = {
            'text': new_text,
            'group': PostCreateFormTests.group2.id
        }
        post = PostCreateFormTests.post
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.get(id=post.id).text,
                         new_text)
        self.assertEqual(Post.objects.get(id=post.id).group.id,
                         PostCreateFormTests.group2.id)
        self.assertEqual(Post.objects.get(id=post.id).author.id,
                         PostCreateFormTests.user.id)
        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': post.id}))
