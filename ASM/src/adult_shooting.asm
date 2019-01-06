adult_shooting_gallery_fix:

	LH		T2, 0xA604 (T2) ; Displaced
	ADDIU	T4, R0, 0x0002  ; Displaced
	
	ADDIU	SP, SP, -0x60
	SW		T2, 0x10 (SP)
	SW		T4, 0x30 (SP)
	SW		T5, 0x40 (SP)
	
	LA		T2, SAVE_CONTEXT 
	LB		T2, 0xA3 (T2)
	ANDI	T2, T2, 0x03 ; T2 has the 2 bits for quiver
	
	LUI		T4, 0x801E
	ADDIU	T4, T4, 0x4084 ; T4 points to the "Not enough rupees" text
	
	BNEZ T2, @@has_bow
	NOP
	
	ADDIU	T5, R0, 0x002C
	SH		T5, 0x00 (T4)
	NOP

	LW		T2, 0x10 (SP)
	LW		T4, 0x30 (SP)
	LW		T5, 0x40 (SP)
	ADDIU	SP, SP, 0x60
	
	ADDIU	V1, R0, 0x0002
	SH 		T4, 0x0200 (S0)
	J		0x801E36D0
	NOP

@@has_bow:

	ADDIU	T5, R0, 0x00C8
	SH		T5, 0x00 (T4)
	NOP

	LW		T2, 0x10 (SP)
	LW		T4, 0x30 (SP)
	LW		T5, 0x40 (SP)
	ADDIU	SP, SP, 0x60
	
	JR		RA
	NOP
	