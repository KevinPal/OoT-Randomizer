#ifndef TRADE_H
#define TRADE_H

#include "z64.h"

void update_inventory();
void give_trade(z64_file_t *save, int16_t arg1, int16_t arg2);
void handle_trade_quest();

#endif
