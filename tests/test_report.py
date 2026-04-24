import polars as pl

from eco2 import report
from tests.data import ROOT


def test_graph_report():
    r = report.GraphReport(ROOT / 'ReportGraph.xls')
    assert isinstance(r.raw, pl.DataFrame)
    assert isinstance(r.data, pl.DataFrame)


def test_upload_report():
    r = report.UploadReport(ROOT / 'ReportUpload.xls')
    assert isinstance(r.raw, pl.DataFrame)
    assert isinstance(r.data, pl.DataFrame)


def test_calculations_report():
    r = report.CalculationsReport(ROOT / 'ReportTotal.xls')
    assert isinstance(r.raw, pl.DataFrame)
    assert isinstance(r.data, pl.DataFrame)


def test_batchreport():
    r = report.BatchReport(ROOT / 'batchreport.tab')
    assert isinstance(r.raw, pl.DataFrame)
    assert isinstance(r.data, pl.DataFrame)
