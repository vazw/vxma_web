import asyncio

from vxma_d import app, webapp


def main():
    web = webapp.app.run(debug=True)
    while True:
        asyncio.run(app.run_bot())


if __name__ == "__main__":
    main()
