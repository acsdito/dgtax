class QueryValidationError(Exception):
    """
    Erro lançado quando a consulta SQL gerada não passa nas regras de segurança.
    """


class LLMResponseFormatError(Exception):
    """
    Erro para indicar que a resposta da IA não está no formato esperado.
    """


class QueryExecutionError(Exception):
    """
    Erro encapsulando falhas na execução da consulta no banco de dados.
    """
