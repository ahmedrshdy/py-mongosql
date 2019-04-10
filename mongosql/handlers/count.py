from __future__ import absolute_import

from sqlalchemy import func
from sqlalchemy import exc as sa_exc

from .base import MongoQueryHandlerBase
from ..exc import InvalidQueryError, InvalidColumnError, InvalidRelationError


class MongoCount(MongoQueryHandlerBase):
    """ MongoDB count query

        Just give it:
        * count=True
    """

    query_object_section_name = 'count'

    def __init__(self, model):
        """ Init a count

        :param model: Sqlalchemy model to work with
        """
        super(MongoCount, self).__init__(model)

        # On input
        self.count = None

    def input_prepare_query_object(self, query_object):
        # When we count, we don't care about certain things
        if query_object.get('count', False):
            # Performance: do not sort when counting
            query_object.pop('sort', None)
            # We don't care about projections either
            query_object.pop('project', None)
            # Also, remove all skips & limits
            query_object.pop('skip', None)
            query_object.pop('limit', None)
            # Finally, when we count, we have to remove `max_items` setting from MongoLimit.
            # Only MongoLimit can do it, and it will do it for us.
            # See: MongoLimit.input_prepare_query_object

        return query_object

    def input(self, count=None):
        super(MongoCount, self).input(count)
        if not isinstance(count, (int, bool, NoneType)):
            raise InvalidQueryError('Count must be either true or false. Or at least a 1, or a 0')

        # Done
        self.count = count
        return self

    def _get_supported_bags(self):
        return None  # not used by this class

    # Not Implemented for this Query Object handler
    compile_columns = NotImplemented
    compile_options = NotImplemented
    compile_statement = NotImplemented
    compile_statements = NotImplemented

    def alter_query(self, query, as_relation=None):
        """ Apply offset() and limit() to the query """
        if self.count:
            # Previously, we used to do counts like this:
            # >>> query = query.with_entities(func.count())
            # However, when there's no WHERE clause set on a Query, it's left without any reference to the target table.
            # In this case, SqlAlchemy will actually generate a query without a FROM clause, which gives a wrong count!
            # Therefore, we have to make sure that there will always be a FROM clause.
            #
            # Normally, we just do the following:
            # >>> query = query.select_from(self.model)
            # This is supposed to indicate which table to select from.
            # However, it can only be applied when there's no FROM nor ORDER BY clauses present.
            #
            # But wait a second... didn't we just assume that there would be no FROM clause?
            # Have a look at this ugly duckling:
            # >>> Query(User).filter_by().select_from(User)
            # This filter_by() would actually create an EMPTY condition, which will break select_from()'s assertions!
            # This is reported to SqlAlchemy:
            # https://github.com/sqlalchemy/sqlalchemy/issues/4606
            # And (is fixed in version x.x.x | is not going to be fixed)
            #
            # Therefore, we'll try to do it the nice way ; and if it fails, we'll have to do something else.
            try:
                query = query.with_entities(func.count()).select_from(self.model)
            except sa_exc.InvalidRequestError:
                query = query.from_self(func.count())

        return query


NoneType = type(None)
