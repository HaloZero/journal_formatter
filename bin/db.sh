#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGDATA="$PROJECT_ROOT/data/postgres"
PGLOG="$PROJECT_ROOT/data/postgres.log"
PGPORT="${PGPORT:-5433}"
PG_BIN="${PG_BIN:-/opt/homebrew/bin/}"

cmd="${1:-}"

case "$cmd" in
	init)
		if [ -d "$PGDATA" ]; then
			echo "Data directory already exists at $PGDATA"
			exit 1
		fi
		mkdir -p "$PROJECT_ROOT/data"
		"$PG_BIN/initdb" --locale=en_US.UTF-8 -E UTF-8 -D "$PGDATA"
		;;
	start)
		"$PG_BIN/pg_ctl" -D "$PGDATA" -o "-p $PGPORT" -l "$PGLOG" start
		;;
	stop)
		"$PG_BIN/pg_ctl" -D "$PGDATA" stop
		;;
	restart)
		"$PG_BIN/pg_ctl" -D "$PGDATA" -o "-p $PGPORT" -l "$PGLOG" restart
		;;
	status)
		"$PG_BIN/pg_ctl" -D "$PGDATA" status
		;;
	create)
		"$PG_BIN/createdb" -p "$PGPORT" journal_python
		;;
	*)
		echo "Usage: $0 {init|start|stop|restart|status|create}"
		exit 1
		;;
esac
