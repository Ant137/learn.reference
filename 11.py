#!/usr/bin/env python
# -*- coding:utf-8 -*-
import curses


# print("=====字体颜色======")
# for i in range(31, 38):
#     print("\033[%s;40mHello world!\033[0m" % i)
# # 背景颜色
# print("=====背景颜色======")
# for i in range(41, 48):
#     print("\033[47;%smHello world!\033[0m" % i)
# # 显示方式
# print("=====显示方式======")
# for i in range(1, 9):
#     print("\033[%s;31;40mHello world!\033[0m" % i)

a = "hello world"

print("\033[31;44m%s\033[0m" % a)
