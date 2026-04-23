#!/usr/bin/env bash
set -euo pipefail

DEBUG=0

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log_line() {
    local emoticon="$1"
    local func="$2"
    local line="$3"
    local message="$4"
    local params="${5:-}"
    printf '[%s] [%s] [compile-latex] [%s:%s] %s | %s\n' "$emoticon" "$(timestamp)" "$func" "$line" "$message" "$params" >&2
}

log_info() {
    log_line 'information_source' "${FUNCNAME[1]:-main}" "${BASH_LINENO[0]:-0}" "$1" "${2:-}"
}

log_warn() {
    log_line 'warning' "${FUNCNAME[1]:-main}" "${BASH_LINENO[0]:-0}" "$1" "${2:-}"
}

log_error() {
    log_line 'x' "${FUNCNAME[1]:-main}" "${BASH_LINENO[0]:-0}" "$1" "${2:-}"
}

log_debug() {
    if [[ "$DEBUG" -eq 1 ]]; then
        log_line 'bug' "${FUNCNAME[1]:-main}" "${BASH_LINENO[0]:-0}" "$1" "${2:-}"
    fi
}

usage() {
    printf 'Uso: %s [--debug] arquivo.tex\n' "$(basename "$0")"
}

run_latexmk() {
    local workdir="$1"
    local filename="$2"
    log_info 'Compilando com latexmk' "workdir=$workdir, arquivo=$filename"
    (
        cd "$workdir"
        latexmk -pdf -interaction=nonstopmode -halt-on-error "$filename"
    )
}

run_pdflatex() {
    local workdir="$1"
    local filename="$2"
    log_info 'Compilando com pdflatex' "workdir=$workdir, arquivo=$filename, passagens=2"
    (
        cd "$workdir"
        pdflatex -interaction=nonstopmode -halt-on-error "$filename"
        pdflatex -interaction=nonstopmode -halt-on-error "$filename"
    )
}

main() {
    local tex_path=''

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --debug)
                DEBUG=1
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                if [[ -n "$tex_path" ]]; then
                    log_error 'Mais de um arquivo informado' "arquivo_atual=$1, arquivo_anterior=$tex_path"
                    usage
                    exit 1
                fi
                tex_path="$1"
                ;;
        esac
        shift
    done

    if [[ -z "$tex_path" ]]; then
        log_error 'Nenhum arquivo .tex foi informado' ''
        usage
        exit 1
    fi

    if [[ ! -f "$tex_path" ]]; then
        log_error 'Arquivo .tex não encontrado' "arquivo=$tex_path"
        exit 1
    fi

    if [[ "${tex_path##*.}" != 'tex' ]]; then
        log_error 'O arquivo informado não possui extensão .tex' "arquivo=$tex_path"
        exit 1
    fi

    local abs_tex
    abs_tex="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$tex_path")"
    local workdir
    workdir="$(dirname "$abs_tex")"
    local filename
    filename="$(basename "$abs_tex")"
    local pdf_path
    pdf_path="$workdir/${filename%.tex}.pdf"

    log_debug 'Parâmetros resolvidos' "abs_tex=$abs_tex, workdir=$workdir, filename=$filename, pdf=$pdf_path"

    if command -v latexmk >/dev/null 2>&1; then
        run_latexmk "$workdir" "$filename"
    elif command -v pdflatex >/dev/null 2>&1; then
        log_warn 'latexmk não encontrado; usando fallback com pdflatex' "arquivo=$filename"
        run_pdflatex "$workdir" "$filename"
    else
        log_error 'Nenhum compilador LaTeX disponível' 'requer=latexmk ou pdflatex'
        exit 1
    fi

    if [[ ! -f "$pdf_path" ]]; then
        log_error 'Compilação finalizada sem gerar PDF' "pdf=$pdf_path"
        exit 1
    fi

    log_info 'PDF gerado com sucesso' "pdf=$pdf_path"
    printf '%s\n' "$pdf_path"
}

main "$@"
