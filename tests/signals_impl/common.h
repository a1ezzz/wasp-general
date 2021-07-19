#ifndef _COMMON_H
#define _COMMON_H

#include <stdio.h>

#define ASSERT_STM(stmt, msg, ...) \
    if (stmt){ \
        fprintf(stderr, msg, ##__VA_ARGS__); \
        fprintf(stderr, "\n"); \
        abort(); \
    }

#endif // _COMMON_H
