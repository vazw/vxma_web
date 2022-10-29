from vxma_d import app, webapp


def main():
    bot = app.run_bot()
    web = webapp.app.run(debug=True)


if __name__ == "__main__":
    main()
