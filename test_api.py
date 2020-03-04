from api import Company
from api import Tag
from api import app
from api import db
from flask_testing import TestCase


class APITestCase(TestCase):
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:wantedrestapi@localhost:5432/test_postgres'
    TESTING = True

    def create_app(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = self.SQLALCHEMY_DATABASE_URI
        return app

    def setUp(self):
        db.create_all()

        self.company_1 = Company(
            company_name_ko='원티드랩',
            company_name_en='Wantedlab',
        )
        self.company_2 = Company(
            company_name_ko='SM Entertainment Japan',
            company_name_ja='株式会社SM Entertainment Japan'
        )
        self.tag_1 = Tag(
            tag_ko='태그_1',
            tag_en='tag_1',
            tag_ja='タグ_1',
        )
        self.company_1.company_tag_set.append(self.tag_1)
        db.session.add(self.company_1)
        db.session.add(self.company_2)
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_search_for_a_company_by_exact_company_name(self):
        """
        정확한 회사명으로 회사를 검색할 수 있다.
        """
        response = self.client.get('/companies', query_string={'name': '원티드랩'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            [
                {
                    'id': self.company_1.id,
                    'name_ko': self.company_1.company_name_ko,
                    'name_en': self.company_1.company_name_en,
                    'name_ja': self.company_1.company_name_ja,
                },
            ]
        )

    def test_search_for_a_company_by_a_part_of_company_name(self):
        """
        회사명의 일부로 회사를 검색할 수 있다.
        """
        client = self.app.test_client()
        response = client.get('/companies', query_string={'name': '원티드'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            [
                {
                    'id': self.company_1.id,
                    'name_ko': self.company_1.company_name_ko,
                    'name_en': self.company_1.company_name_en,
                    'name_ja': self.company_1.company_name_ja,
                }
            ]
        )

    def test_search_for_a_company_by_english_company_name(self):
        """
        영어 회사명으로 회사를 검색할 수 있다.
        """
        response = self.client.get('/companies', query_string={'name': 'Sm '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            [
                {
                    'id': self.company_2.id,
                    'name_ko': self.company_2.company_name_ko,
                    'name_en': self.company_2.company_name_en,
                    'name_ja': self.company_2.company_name_ja,
                }
            ]
        )

    def test_search_for_a_company_by_japanese_company_name(self):
        """
        일본어 회사명으로 회사를 검색할 수 있다.
        """
        response = self.client.get('/companies', query_string={'name': '株式会'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            [
                {
                    'id': self.company_2.id,
                    'name_ko': self.company_2.company_name_ko,
                    'name_en': self.company_2.company_name_en,
                    'name_ja': self.company_2.company_name_ja,
                }
            ]
        )

    def test_search_for_a_company_by_korean_tag_name(self):
        """
        한글 태그명으로 회사를 검색할 수 있다.
        """
        response = self.client.get('/companies', query_string={'tag': '태그_1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            [
                {
                    'id': self.company_1.id,
                    'name_ko': self.company_1.company_name_ko,
                    'name_en': self.company_1.company_name_en,
                    'name_ja': self.company_1.company_name_ja,
                }
            ]
        )

    def test_add_tag_name_of_company(self):
        """
        회사의 태그 정보를 추가할 수 있다.
        """
        params = {
            'tag_ko': '태그_100',
            'tag_en': 'tag_100',
            'tag_ja': 'タグ_100',
        }
        response = self.client.post('/tags', data=params)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json,
            {
                'name_ko': params['tag_ko'],
                'name_en': params['tag_en'],
                'name_ja': params['tag_ja'],
            }
        )

    def test_tag_name_must_entered_all_languages(self):
        """
        모든 언어에 대한 태그명이 입력되지않으면 에러가 발생한다.
        """
        params = {
            'tag_ko': '태그_100',
            'tag_en': 'tag_100',
        }
        response = self.client.post('/tags', data=params)
        self.assertEqual(response.status_code, 400)

    def test_delete_tag_name_of_company(self):
        """
        회사의 태그 정보를 삭제할 수 있다.
        """
        origin_len = len(Tag.query.all())

        response = self.client.delete(
            '/tag/{}'.format(Tag.query.all()[0].id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(Tag.query.all()), origin_len - 1
        )

    def test_delete_tag_name_exist_tag(self):
        """
        입력한 id에 해당하는 Tag값이 존재하지 않으면 삭제 시 에러가 발생한다.
        """
        response = self.client.delete('/tag/239482384')
        self.assertEqual(response.status_code, 400)
