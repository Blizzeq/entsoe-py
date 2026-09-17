from itertools import product
import os
import warnings
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
from entsoe.decorators import documents_limited
from entsoe.exceptions import NoMatchingDataError
import pandas as pd
import pytest

load_dotenv()

API_KEY = os.getenv("API_KEY")


@pytest.fixture
def client():
    yield EntsoePandasClient(api_key=API_KEY)


# this on purpose more then a month since entsoe has now a lot of "30 days" limits
STARTS = [pd.Timestamp("20260301", tz="Europe/Amsterdam")]
ENDS = [pd.Timestamp("20260402 23:59", tz="Europe/Amsterdam")]

COUNTRY_CODES = ["NL", "BE", "DE_LU", "FR"]
COUNTRY_CODES_FROM = ["NL"]
COUNTRY_CODES_TO = ["DE_LU", 'NO_2', 'BE']

BASIC_QUERIES_TIMESERIES = [
    "query_day_ahead_prices",
    "query_net_position",
    "query_load",
    "query_load_forecast",
    "query_wind_and_solar_forecast",
    "query_generation_forecast",
    "query_generation",
    "query_generation_per_plant",
    "query_installed_generation_capacity",
    "query_current_balancing_state"
]

BASIC_QUERIES = [
    "query_installed_generation_capacity_per_unit",
]

BASIC_QUERIES_TIMESERIES_ZIP = [
    "query_imbalance_prices",
    "query_imbalance_volumes",
]

CROSSBORDER_QUERIES = [
    "query_crossborder_flows",
    "query_scheduled_exchanges",
    "query_net_transfer_capacity_dayahead",
    "query_net_transfer_capacity_weekahead",
    "query_net_transfer_capacity_monthahead",
    #"query_net_transfer_capacity_yearahead",
]

def basic_checks(result, timeseries=True):
    assert isinstance(result, pd.Series) or isinstance(result, pd.DataFrame)
    assert not result.empty
    if timeseries:
        assert result.index.is_monotonic_increasing and result.index.is_unique

    if isinstance(result, pd.Series):
        assert not result.isna().all()
    elif isinstance(result, pd.DataFrame):
        assert not result.isna().all().all()

@pytest.mark.parametrize(
    "country_code, start, end, query",
    product(COUNTRY_CODES, STARTS, ENDS, BASIC_QUERIES_TIMESERIES),
)
def test_basic_queries_timeseries(client, query, country_code, start, end):
    if query == 'query_current_balancing_state' and country_code == 'DE_LU':
        country_code = 'DE_AMPRION'
    if query == 'query_generation_per_plant' and country_code == 'DE_LU':
        # this is bugged, ticket raised at entsoe
        return
    result = getattr(client, query)(country_code, start=start, end=end)
    basic_checks(result)

@pytest.mark.parametrize(
    "country_code, start, end, query",
    product(COUNTRY_CODES, STARTS, ENDS, BASIC_QUERIES),
)
def test_basic_queries(client, query, country_code, start, end):
    result = getattr(client, query)(country_code, start=start, end=end)
    basic_checks(result, timeseries=False)



@pytest.mark.parametrize(
    "country_code, start, end, query",
    product(['BE', 'FR'], STARTS, ENDS, BASIC_QUERIES_TIMESERIES_ZIP),
)
def test_basic_queries_zip(client, query, country_code, start, end):
    result = getattr(client, query)(country_code, start=start, end=end)
    basic_checks(result)



@pytest.mark.parametrize(
    "country_code_from, country_code_to, start, end, query",
    product(COUNTRY_CODES_FROM, COUNTRY_CODES_TO, STARTS, ENDS, CROSSBORDER_QUERIES),
)
def test_crossborder_queries(
    client, query, country_code_from, country_code_to, start, end
):
    result = getattr(client, query)(country_code_from, country_code_to, start=start, end=end)
    basic_checks(result)


def test_query_aggregate_water_reservoirs_and_hydro_storage(client):
    result = client.query_aggregate_water_reservoirs_and_hydro_storage('NO_2',
                                                                       start=STARTS[0], end=ENDS[0])
    basic_checks(result)


@pytest.mark.parametrize(
    "country_code_from, country_code_to, start, end, id_type",
    [x for x in product(["BE", "NL"], ["BE", "NL"], STARTS, ENDS, ['IDCT', 'IDA1', 'IDA2', 'IDA3']) if x[0] != x[1]],
)
def test_query_intraday_offered_capacity(client, country_code_from, country_code_to, start, end, id_type):
    result = client.query_intraday_offered_capacity(
        country_code_from, country_code_to, start=start, end=end, implicit=True, id_type=id_type
    )
    basic_checks(result)


# @pytest.mark.parametrize(
#     "country_code, process_type, start, end",
#     product([x if x != 'DE_LU' else 'DE_AMPRION' for x in COUNTRY_CODES], ['A51', 'A52', 'A47'], STARTS, ENDS),
# )
# def test_query_contracted_reserve_prices_procured_capacity(client, country_code, process_type, start, end):
#     # [O] A51 = Automatic frequency restoration reserve; A52 = Frequency containment reserve; A47 = Manual frequency restoration reserve; A46 = Replacement reserve
#     result = client.query_contracted_reserve_prices_procured_capacity(
#         country_code, start=start, end=end, process_type=process_type, type_marketagreement_type='A01'
#     )
#     basic_checks(result)


@pytest.mark.parametrize(
    "country_code, start, end",
    product(COUNTRY_CODES, STARTS, ENDS),
)
def test_query_unavailability_of_generation_units(client, country_code, start, end):
    result = client.query_unavailability_of_generation_units(country_code, start=start, end=end, docstatus=None, periodstartupdate=None, periodendupdate=None)
    basic_checks(result, timeseries=False)


@pytest.mark.parametrize(
    "country_code, start, end",
    product([x for x in COUNTRY_CODES if x != 'BE'], STARTS, ENDS),
)
def test_query_unavailability_of_production_units(client, country_code, start, end):
    result = client.query_unavailability_of_production_units(country_code, start=start, end=end, docstatus=None, periodstartupdate=None, periodendupdate=None)
    basic_checks(result, timeseries=False)

@pytest.mark.parametrize(
    "country_code_from, country_code_to, start, end",
    product(COUNTRY_CODES_FROM, [x for x in COUNTRY_CODES_TO if x != 'DE_LU'], STARTS, ENDS),
)
def test_query_unavailability_transmission(
    client, country_code_from, country_code_to, start, end
):
    result = client.query_unavailability_transmission(
        country_code_from, country_code_to, start=start, end=end, docstatus=None, periodstartupdate=None, periodendupdate=None
    )
    basic_checks(result, timeseries=False)

@pytest.mark.parametrize(
    "country_code, start, end",
    product(COUNTRY_CODES, STARTS, ENDS),
)
def test_query_withdrawn_unavailability_of_generation_units(
    client, country_code, start, end
):
    result = client.query_withdrawn_unavailability_of_generation_units(
        country_code, start, end,
    )
    basic_checks(result, timeseries=False)


# The query functions below stand in for the API layer so these run offline,
# the decorator under test is the real one. Offset cap handling per #544.
PAGE_SIZE = 200
OFFSET_CAP = 4800


def page(offset: int) -> pd.DataFrame:
    """One document, identified by the offset it was fetched at."""
    return pd.DataFrame({"offset": [offset]}, index=[pd.Timestamp("2026-01-01") + pd.Timedelta(hours=offset)])


@documents_limited(PAGE_SIZE)
def query_endless(*args, offset=0, **kwargs):
    """A server that never says it is out of data."""
    return page(offset)


@documents_limited(PAGE_SIZE)
def query_three_pages(*args, offset=0, **kwargs):
    """A server that runs out of data well before the cap."""
    if offset >= 3 * PAGE_SIZE:
        raise NoMatchingDataError
    return page(offset)


def test_documents_limited_warns_when_it_stops_at_the_cap():
    with pytest.warns(UserWarning, match="offset limit"):
        result = query_endless()

    # Every offset up to and including the cap was fetched, as before.
    assert list(result["offset"]) == list(range(0, OFFSET_CAP + PAGE_SIZE, PAGE_SIZE))


def test_documents_limited_is_quiet_when_the_data_runs_out():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = query_three_pages()

    assert list(result["offset"]) == [0, PAGE_SIZE, 2 * PAGE_SIZE]


def test_documents_limited_still_raises_when_there_is_nothing():
    @documents_limited(PAGE_SIZE)
    def query_empty(*args, offset=0, **kwargs):
        raise NoMatchingDataError

    with pytest.raises(NoMatchingDataError):
        query_empty()
