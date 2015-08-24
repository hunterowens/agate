#!/usr/bin/env python

from collections import defaultdict
import datetime

from journalism.column_types import BooleanType, NumberType
from journalism.columns import BooleanColumn, DateColumn, DateTimeColumn, NumberColumn, TextColumn
from journalism.exceptions import NullComputationError, UnsupportedAggregationError

class Aggregation(object): #pragma: no cover
    """
    Base class defining an operation that can be performed on a column either
    to yield an individual value or as part of a :class:`.TableSet` aggregate.
    """
    def get_aggregate_column_type(self, column):
        raise NotImplementedError()

    def run(self, column):
        raise NotImplementedError()

class NonNullAggregation(Aggregation):
    """
    Base class for aggregations that can only be applied to columns which do
    not contain nulls.
    """
    def run(self, column):
        if column.summarize(HasNulls()):
            raise NullComputationError

class HasNulls(Aggregation):
    """
    Returns :code:`True` if this column contains null values.
    """
    def get_aggregate_column_type(self, column):
        return BooleanType()

    def run(self, column):
        return column._has_nulls()

class Any(Aggregation):
    """
    Returns :code:`True` if any value passes a truth test. The truth test may
    be omitted when testing a :class:`.BooleanColumn`.

    :param test: A function that takes a value and returns :code:`True`
        or :code:`False`.
    """
    def __init__(self, test=None):
        self._test = test

    def get_aggregate_column_type(self, column):
        return BooleanType()

    def run(self, column):
        data = column._data()

        if isinstance(column, BooleanColumn):
            return any(data)
        elif not self._test:
            raise ValueError('You must supply a test function for non-BooleanColumn.')

        return any(self._test(d) for d in data)

class All(Aggregation):
    """
    Returns :code:`True` if all values pass a truth test. The truth test may
    be omitted when testing a :class:`.BooleanColumn`.

    :param test: A function that takes a value and returns :code:`True`
        or :code:`False`.
    """
    def __init__(self, test=None):
        self._test = test

    def get_aggregate_column_type(self, column):
        return BooleanType()

    def run(self, column):
        data = column._data()

        if isinstance(column, BooleanColumn):
            return all(data)
        elif not self._test:
            raise ValueError('You must supply a test function for non-BooleanColumn.')

        return all(self._test(d) for d in data)

class Count(Aggregation):
    """
    Count the number of times a specific value occurs in this column.

    :param value: The value to be counted.
    """
    def __init__(self, value):
        self._value = value

    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        count = 0

        for d in column._data():
            if d == self._value:
                count += 1

        return count

class Min(Aggregation):
    """
    Compute the minimum value in this column. May be applied to
    :class:`.DateColumn`, :class:`.DateTimeColumn` and :class:`.NumberColumn`.

    :returns: :class:`datetime.date`.
    """
    def get_aggregate_column_type(self, column):
        if isinstance(column, DateColumn):
            return DateType()
        elif isinstance(column, DateTimeColumn):
            return DateTimeType()
        elif isinstance(column, NumberColumn):
            return NumberType()

    def run(self, column):
        supported_columns = (DateColumn, DateTimeColumn, NumberColumn)

        if not any(isinstance(column, t) for t in supported_columns):
            raise UnsupportedAggregationError(self, column)

        return min(column._data_without_nulls())

class Max(Aggregation):
    """
    Compute the maximum value in this column. May be applied to
    :class:`.DateColumn`, :class:`.DateTimeColumn` and :class:`.NumberColumn`.

    :returns: :class:`datetime.date`.
    """
    def get_aggregate_column_type(self, column):
        if isinstance(column, DateColumn):
            return DateType()
        elif isinstance(column, DateTimeColumn):
            return DateTimeType()
        elif isinstance(column, NumberColumn):
            return NumberType()

    def run(self, column):
        supported_columns = (DateColumn, DateTimeColumn, NumberColumn)

        if not any(isinstance(column, t) for t in supported_columns):
            raise UnsupportedAggregationError(self, column)

        return max(column._data_without_nulls())

class Sum(Aggregation):
    """
    Compute the sum of this column.

    :returns: :class:`decimal.Decimal`.
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        return sum(column._data_without_nulls())

class Mean(NonNullAggregation):
    """
    Compute the mean value of this column.

    :returns: :class:`decimal.Decimal`.
    :raises: :exc:`.NullComputationError`
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        super(Mean, self).run(column)

        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        return column.summarize(Sum()) / len(column)

class Median(NonNullAggregation):
    """
    Compute the median value of this column.

    This is the 50th percentile. See :class:`Percentiles` for implementation
    details.

    :returns: :class:`decimal.Decimal`.
    :raises: :exc:`.NullComputationError`
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        super(Median, self).run(column)

        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        return column.percentiles()[50]

class Mode(NonNullAggregation):
    """
    Compute the mode value of this column.

    :returns: :class:`decimal.Decimal`.
    :raises: :exc:`.NullComputationError`
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        super(Mode, self).run(column)

        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        data = column._data()
        state = defaultdict(int)

        for n in data:
            state[n] += 1

        return max(state.keys(), key=lambda x: state[x])

class IQR(NonNullAggregation):
    """
    Compute the inter-quartile range of this column.

    :returns: :class:`decimal.Decimal`.
    :raises: :exc:`.NullComputationError`
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        super(IQR, self).run(column)

        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        percentiles = column.percentiles()

        return percentiles[75] - percentiles[25]

class Variance(NonNullAggregation):
    """
    Compute the variance of this column.

    :returns: :class:`decimal.Decimal`.
    :raises: :exc:`.NullComputationError`
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        super(Variance, self).run(column)

        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        data = column._data()
        mean = column.summarize(Mean())

        return sum((n - mean) ** 2 for n in data) / len(data)

class StDev(NonNullAggregation):
    """
    Compute the standard of deviation of this column.

    :returns: :class:`decimal.Decimal`.
    :raises: :exc:`.NullComputationError`
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        super(StDev, self).run(column)

        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        return column.summarize(Variance()).sqrt()

class MAD(NonNullAggregation):
    """
    Compute the `median absolute deviation <http://en.wikipedia.org/wiki/Median_absolute_deviation>`_
    of this column.

    :returns: :class:`decimal.Decimal`.
    :raises: :exc:`.NullComputationError`
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def _median(self, data_sorted):
        length = len(data_sorted)

        if length % 2 == 1:
            return data_sorted[((length + 1) // 2) - 1]

        half = length // 2
        a = data_sorted[half - 1]
        b = data_sorted[half]

        return (a + b) / 2

    def run(self, column):
        super(MAD, self).run(column)

        if not isinstance(column, NumberColumn):
            raise UnsupportedAggregationError(self, column)

        data = column._data_sorted()
        m = column.percentiles()[50]

        return self._median(tuple(abs(n - m) for n in data))

class MaxLength(Aggregation):
    """
    Calculates the longest string in this column.
    """
    def get_aggregate_column_type(self, column):
        return NumberType()

    def run(self, column):
        if not isinstance(column, TextColumn):
            raise UnsupportedAggregationError(self, column)

        return max([len(d) for d in column._data_without_nulls()])
