"""news app DRF 端點。

回傳原始 payload（鏡射原 data/*.json，逐欄位一致，不套公司信封層，
與既有 apiserver 風格一致）。所有端點皆為 GET。
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from news import store


@api_view(["GET"])
def market(request):
    return Response(store.read_market())


@api_view(["GET"])
def headlines(request):
    return Response(store.read_headlines())


@api_view(["GET"])
def tsmc(request):
    return Response(store.read_tsmc())


@api_view(["GET"])
def fed(request):
    return Response(store.read_fed())


@api_view(["GET"])
def heat(request):
    return Response(store.read_heat())


@api_view(["GET"])
def events(request):
    return Response(store.read_events())


@api_view(["GET"])
def watchlist(request):
    return Response(store.read_watchlist())


@api_view(["GET"])
def summary(request):
    return Response(store.read_summary())


@api_view(["GET"])
def status_view(request):
    return Response(store.read_status())


@api_view(["GET"])
def valuation_default(request):
    payload = store.read_valuation()
    if payload is None:
        return Response({"detail": "no valuation data"}, status=status.HTTP_404_NOT_FOUND)
    return Response(payload)


@api_view(["GET"])
def valuation_by_code(request, code):
    payload = store.read_valuation(code)
    if payload is None:
        return Response({"detail": "valuation not found: {}".format(code)},
                        status=status.HTTP_404_NOT_FOUND)
    return Response(payload)
