from rq import SimpleWorker

from app.queue import plan_queue, redis_conn, research_queue


def main() -> None:
    worker = SimpleWorker([research_queue, plan_queue], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
