import argparse
import asyncio
import csv
import functools
import logging
import re
from datetime import datetime

import aiohttp
from apachelogs import LogEntry, LogParser

logging.basicConfig(
    format="%(asctime)s %(levelname)-5.5s %(message)s",
)

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

URL_BASE_REGEX = re.compile("[htps]+:\/\/(www)?[\w\.]+\/")


def output_jmeter_format(
    resource: dict = {},
    response=None,
    request_start_time: datetime = None,
    request_end_time: datetime = None,
    output_file=None,
    output_only_head=False,
):
    writer = csv.DictWriter(
        output_file,
        fieldnames=[
            "timeStamp",
            "elapsed",
            "label",
            "responseCode",
            "responseMessage",
            "threadName",
            "dataType",
            "success",
            "failureMessage",
            "bytes",
            "sentBytes",
            "grpThreads",
            "allThreads",  # Deveria imprimir a quantidade de threads naquele momento
            "URL",
            "Latency",
            "IdleTime",
            "Connect",
        ],
    )

    if output_only_head:
        writer.writeheader()
        return

    writer.writerow(
        {
            "timeStamp": int(request_start_time.timestamp()),
            "elapsed": int(
                (request_end_time.timestamp() - request_start_time.timestamp()) * 1000
            ),
            "label": str(response.url),
            "responseCode": response.status,
            "responseMessage": response.reason,
            "threadName": "Thread Group",
            "dataType": "text",
            "success": response.ok,
            "failureMessage": "",
            "bytes": 0,
            "sentBytes": 0,
            "grpThreads": 0,
            "allThreads": 1,
            "URL": str(response.url),
            "Latency": 0,
            "IdleTime": 0,
            "Connect": 0,
        }
    )


# Mapeamento dos formatos de saída e suas funções
OUTPUT_FUNCTIONS = {"jmeter": output_jmeter_format}


def main():
    parser = argparse.ArgumentParser("Time Machine")
    parser.add_argument(
        "--connections",
        help="Limite de máximo de conexões concorrentes (default: 50)",
        default=50,
        type=int,
    )
    parser.add_argument(
        "--output-file",
        type=argparse.FileType("w"),
        help="Arquivo de saída com o resultado das requisições",
    )
    parser.add_argument(
        "--output-format",
        default="jmeter",
        choices=["jmeter"],
        help="Formato de saída das requisições",
    )
    parser.add_argument(
        "--dont-wait-until-request-time",
        action="store_true",
        help="Ignora o atraso de tempo da requisição. Utilize quando não quiser"
        " seguir o modo de replay de acessos.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10,
        help="Define o tempo limite que uma requisição deve ser esperada (default: 10)",
    )
    parser.add_argument(
        "log_file",
        type=argparse.FileType("r"),
        help="Arquivo de log em formato Apache",
    )
    parser.add_argument(
        "urlbase",
        default="https://new.scielo.br",
        help="Website utilizado para realizar as requisições (schema + netloc)"
        ", ex: https://www.scielo.br",
    )
    args = parser.parse_args()
    loop = asyncio.get_event_loop()

    if args.output_file is not None:
        outputfunc = OUTPUT_FUNCTIONS.get(args.output_format)
        outputfunc = functools.partial(outputfunc, output_file=args.output_file)
        # Imprime apenas o cabeçalho do CSV
        outputfunc(output_only_head=True)
    else:
        outputfunc = lambda *args, **kwargs: 1

    results = loop.run_until_complete(
        queue_tasks(
            resources=parse_log_access_entries(args.log_file),
            connections=args.connections,
            outputfunc=outputfunc,
            dont_wait_until_request_time=args.dont_wait_until_request_time,
            urlbase=args.urlbase,
            timeout=args.timeout,
        )
    )


def parse_log_access_entries(file):
    """Faz o parser de um LOG no formato Apache e retorna uma lista
    de recursos.

    Também calcula o tempo de atraso com que o recurso deve ser acessado.
    """

    # https://httpd.apache.org/docs/1.3/mod/mod_log_config.html#formats
    parser = LogParser('%h %l %u %t "%m %U %H" %>s %b "%{Referer}i" "%{User-Agent}i"')

    requests = []
    start_time = None
    entries = list(parser.parse_lines(file))

    if entries is not None and len(entries) > 0:
        start_time = entries[0].request_time

    for entry in entries:
        requests.append(
            {
                "path": URL_BASE_REGEX.sub("/", entry.request_uri),
                "method": entry.request_method,
                "delay": (entry.request_time - start_time).total_seconds(),
                "entry": entry.entry,
            }
        )

    return requests


async def queue_tasks(
    resources, connections, outputfunc, dont_wait_until_request_time, urlbase, timeout
):
    """Enfileira as requisições que serão feitas"""

    sem = asyncio.Semaphore(connections)
    tasks = []

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as session:
        for resource in resources:
            task = asyncio.ensure_future(
                bound_fetch(
                    sem,
                    session,
                    fetch_resource,
                    urlbase,
                    resource,
                    functools.partial(outputfunc, resource=resource),
                    dont_wait_until_request_time,
                )
            )
            tasks.append(task)

        if tasks:
            logger.info("Quantidade de tasks registradas: %s" % len(tasks))
            responses = asyncio.gather(*tasks)
            await responses


async def bound_fetch(
    semaphore,
    session,
    fetcher,
    urlbase,
    resource,
    outputfunc,
    dont_wait_until_request_time,
):
    """Encapsula a função que acessa o recurso. Também faz o controle de quantas
    conexões podem ser abertas."""

    delay = resource.get("delay", 0)

    if dont_wait_until_request_time:
        delay = 0

    async with semaphore:
        await fetcher(session, resource, delay, outputfunc=outputfunc, urlbase=urlbase)


async def fetch_resource(
    session,
    resource,
    delay,
    outputfunc,
    urlbase,
):
    """Acessa um recurso a partir de um urlbase definido.

    É possível definir um tempo de espera para que o acesso seja feito."""

    await asyncio.sleep(delay)
    start = datetime.now()

    try:
        async with session.get(f"{urlbase}{resource.get('path')}") as response:
            end = datetime.now()
            elapsed = end - start
            outputfunc(
                response=response, request_start_time=start, request_end_time=end
            )
            logger.info("%s %s %s %s", delay, elapsed, response.status, response.url)
    except aiohttp.client_exceptions.TooManyRedirects:
        pass
    except asyncio.TimeoutError:
        pass
    except aiohttp.client_exceptions.ClientConnectorError:
        pass
    except Exception as e:
        logger.exception("Exceção não tratada")


if __name__ == "__main__":
    main()
