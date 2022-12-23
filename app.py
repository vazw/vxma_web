# The BEERWARE License (BEERWARE)
#
# Copyright (c) 2022 Author. All rights reserved.
#
# Licensed under the "THE BEER-WARE LICENSE" (Revision 42):
# vazw wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer or coffee in return

import asyncio

from vxma_d.AppData import Bot, colorCS

my_message = (
    f"\r{colorCS.CRED}{colorCS.CBOLD}ก่อนที่เราจะเทรด Futures\n"
    + "เราต้องเข้าใจไว้ก่อนว่าเงินนั้นมันอาจจะหมดเป็นศูนย์ได้เลย\n"
    + "หากเราเข้าใจตามนี้แล้วความเสี่ยงทั้งหมดของเงินลงทุนจะเท่ากับ"
    + f"Risk 1 : Reward infinity เสมอ{colorCS.CEND}"
)


def main():
    while True:
        try:
            asyncio.run(Bot.run_bot())
        except KeyboardInterrupt:
            return print(my_message)


if __name__ == "__main__":
    print("Starting VXMA Bot Trading by Vaz")
    main()
