from apscheduler.schedulers.blocking import BlockingScheduler
from waygate_scheduler.config import SchedulerConfig
from asyncio import run

config = SchedulerConfig()


async def main() -> None:
    url = f"postgresql://{config.pg_user}:{config.pg_password}@{config.pg_host}:{config.pg_port}/{config.pg_db}"
    scheduler = BlockingScheduler()
    scheduler.add_jobstore(
        "sqlalchemy",
        url=url,
    )
    try:
        print("Waygate Scheduler is running...")
        scheduler.start()
    except KeyboardInterrupt, SystemExit:
        pass


if __name__ == "__main__":
    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
    try:
        run(main())
    except KeyboardInterrupt, SystemExit:
        pass
