#include "trade.h"
#include "z64.h"


#define adult_trade_items z64_file.scene_flags[0x49].unk_00_ 
#define num_adult_items 11

char adult_selected = 0xFF;

uint32_t dpad_frames = 0;

uint32_t* WQDIWQODIQQWDQWDSIDHAISUHD = &adult_trade_items;
uint32_t debug = 0;
uint32_t debug2 = 0;
uint32_t debug3 = 0;
uint32_t debug4 = 0;
uint32_t debug5 = 0;
uint32_t debug6 = 0;
// Egg | Cucco | Cojiro | Mushroom | Potion | Saw | Sword | Pres | Frog | Eye | Claim

char nextSelection(int age, int direction) {
    if (age == 1) {
        if (adult_trade_items & ((1 << num_adult_items) - 1) == 0) {
            return -1;
        } else {
            do {
                adult_selected += direction;
                if (adult_selected < 0) {
                    adult_selected += num_adult_items;
                }
                adult_selected %= num_adult_items;
            } while(((1 << adult_selected) & adult_trade_items) == 0);
        }
    }
}

void handle_trade_quest() {
    update_inventory();
    if (dpad_frames > 0) {
        dpad_frames--;
        return;
    } else if(z64_game.pause_ctxt.state == 6 && z64_game.pause_ctxt.screen_idx == 0) {
        if (z64_game.pause_ctxt.item_cursor == 0x16) {
            if (z64_ctxt.input[0].raw.pad.dl) {
                adult_selected = nextSelection(1, -1);
                dpad_frames = 5;
            } else if (z64_ctxt.input[0].raw.pad.dr) {
                adult_selected = nextSelection(1, 1);
                dpad_frames = 5;
            }
        }
    }
}
void update_inventory() {
    if (z64_file.items[22] != (0x2D + adult_selected) && adult_selected != -1) {
        // We had an item before, but its gone now. Assume it was traded
        adult_trade_items &= ~(1 << adult_selected);
        adult_selected = nextSelection(1, 1);
    }

    if (adult_selected != -1) {
        z64_file.items[22] = 0x2D + adult_selected;
    } else {
        z64_file.items[22] = 0xFF;
    }
}

// This is an item effect defined in the item table
// 0 -> child, 1 -> adult
void give_trade(z64_file_t *save, int16_t age, int16_t item) {
    z64_file.items[0] = 7;
    if(age == 1) { //Adult trade
        adult_trade_items |= (1 << item);

        if (adult_selected == -1) {
            adult_selected = item;
            z64_file.items[22] = 0x2D + adult_selected;
        }
    }

    update_inventory();
}

