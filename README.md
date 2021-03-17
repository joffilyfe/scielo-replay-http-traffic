# SciELO Replay HTTP Traffic

Esta é uma aplicação capaz de simular o tráfego de requisições HTTP a um serviço utilizando um arquivo de log em formato Apache.

## Interface de utilização

```shell
usage: Time Machine [-h] [--connections CONNECTIONS]
                    [--output-file OUTPUT_FILE] [--output-format {jmeter}]
                    [--dont-wait-until-request-time]
                    log_file urlbase

positional arguments:
  log_file              Arquivo de log em formato Apache
  urlbase               Website utilizado para realizar as requisições (schema
                        + netloc), ex: https://www.scielo.br

optional arguments:
  -h, --help            show this help message and exit
  --connections CONNECTIONS
                        Limite de máximo de conexões concorrentes (default:
                        50)
  --output-file OUTPUT_FILE
                        Arquivo de saída com o resultado das requisições
  --output-format {jmeter}
                        Formato de saída das requisições
  --dont-wait-until-request-time
                        Ignora o atraso de tempo da requisição. Utilize quando
                        não quiser seguir o modo de replay de acessos.
```

A aplicação pode ser executada utilizando apenas dois parâmetros obrigatórios (`log_file` e `urlbase`). O arquivo de log utilizado deve seguir o padrão [apache](https://httpd.apache.org/docs/1.3/mod/mod_log_config.html#formats), já o parâmetro `urlbase` deve seguir o padrão `schema://+netloc` (ex: `https://www.scielo.br`).

Para registrar em arquivo a execução do programa utilize o parâmetro `--output-file` indicando o caminho do arquivo que será salvo. Em conjunto utilize o parâmetro `--output-format` para determinar qual é o formato da saída.

É possível ignorar o tempo das requisições que está presente no arquivo de log por meio do parâmetro `--dont-wait-until-request-time`. Dessa forma o script fará a leitura do arquivo de log e limitará as requisições a quantidade de conexões do parâmetro `--connections`.
