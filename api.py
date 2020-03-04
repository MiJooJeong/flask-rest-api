import csv
import os

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_restplus import Api
from flask_restplus import Resource
from flask_restplus import abort
from flask_restplus import reqparse
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy.orm.exc import UnmappedInstanceError

load_dotenv()

if os.getenv('env'):
    env = os.getenv('env')
else:
    env = 'LOCAL'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI_{}'.format(env))
title = "A사 API"
description = """
A사 API 입니다.
A사에 등록된 회사와 회사에 등록된 태그 정보를 보여줍니다.
태그 정보를 추가하거나 삭제할 수 있습니다.
"""

api = Api(
    app,
    title=title,
    description=description,
    default='endpoints',
    default_label=''
)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

companies_tags = db.Table(
    'companies_tags',
    db.Column('company_id', db.Integer, db.ForeignKey('company.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    company_name_ko = db.Column(db.String(100))
    company_name_en = db.Column(db.String(100))
    company_name_ja = db.Column(db.String(100))
    company_tag_set = db.relationship('Tag', secondary=companies_tags, backref=db.backref('companies'))

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name_ko': self.company_name_ko,
            'name_en': self.company_name_en,
            'name_ja': self.company_name_ja,
        }


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True, autoincrement=True)
    tag_ko = db.Column(db.String(100))
    tag_en = db.Column(db.String(100))
    tag_ja = db.Column(db.String(100))


company_parser = reqparse.RequestParser()
company_parser.add_argument('name', type=str, help='회사 이름')
company_parser.add_argument('tag', type=str, help='태그명')


def insert_sample_data_from_file():
    """
    원티드에서 제공한 데이터 파일로 부터 RDB에 Company, Tag 모델 생성
    """
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Tag 모델 생성
    for i in range(30):
        tag = Tag(
            tag_ko='태그_{}'.format(i + 1),
            tag_en='tag_{}'.format(i + 1),
            tag_ja='タグ_{}'.format(i + 1)
        )
        db.session.add(tag)
        db.session.commit()

    # Company 모델 생성
    with open(os.path.join(project_dir, 'data_file.csv')) as sample_data_file:
        csv_reader = csv.DictReader(sample_data_file)
        for rows in csv_reader:
            company = Company(
                company_name_ko=rows['company_ko'],
                company_name_en=rows['company_en'],
                company_name_ja=rows['company_ja']
            )
            tag_list = rows['tag_ko'].split('|')
            for tag in tag_list:
                company.company_tag_set.append((Tag.query.filter(Tag.tag_ko == tag)).all()[0])
            db.session.add(company)
            db.session.commit()


@api.route('/companies')
@api.expect(company_parser)
class CompanyApi(Resource):
    def get(self):
        args = company_parser.parse_args()
        name, tag = args['name'], args['tag']
        company_queryset_by_name, company_queryset_by_tag = None, None

        if name:
            name_str = '%{}%'.format(name)
            company_queryset_by_name = Company.query.filter(
                or_(
                    Company.company_name_ko.ilike(name_str),
                    Company.company_name_en.ilike(name_str),
                    Company.company_name_ja.ilike(name_str)
                )
            )

        if tag:
            company_queryset_by_tag = Company.query.join(companies_tags).join(Tag).filter(
                or_(
                    Tag.tag_ko == tag,
                    Tag.tag_en == tag,
                    Tag.tag_ja == tag
                )
            )

        if company_queryset_by_name and company_queryset_by_tag:
            company_queryset = company_queryset_by_name.intersect(company_queryset_by_tag)
        elif company_queryset_by_name:
            company_queryset = company_queryset_by_name
        else:
            company_queryset = company_queryset_by_tag

        return [x.serialize for x in company_queryset.all()]


tag_parser = reqparse.RequestParser()
tag_parser.add_argument('tag_ko', type=str, help='한글 태그명')
tag_parser.add_argument('tag_en', type=str, help='영어 태그명')
tag_parser.add_argument('tag_ja', type=str, help='일본어 태그명')


@api.route('/tags')
@api.expect(tag_parser)
class TagListApi(Resource):
    def post(self):
        args = tag_parser.parse_args()
        tag_ko, tag_en, tag_ja = args['tag_ko'], args['tag_en'], args['tag_ja']
        if not tag_ko or not tag_en or not tag_ja:
            abort(400, message='모든 언어에 대한 태그명이 필요합니다.')

        tag = Tag(
            tag_ko=tag_ko,
            tag_en=tag_en,
            tag_ja=tag_ja,
        )
        db.session.add(tag)
        db.session.commit()
        return {
            'name_ko': tag.tag_ko,
            'name_en': tag.tag_en,
            'name_ja': tag.tag_ja
        }, 201


@api.route('/tag/<int:tag_id>')
class TagApi(Resource):
    def delete(self, tag_id):
        tag = Tag.query.get(tag_id)
        try:
            db.session.delete(tag)
        except UnmappedInstanceError:
            abort(400, '입력한 id에 해당하는 Tag가 존재하지 않습니다.')
        db.session.commit()
        return 'tag delete completed', 200


if __name__ == '__main__':
    app.run(debug=True)
