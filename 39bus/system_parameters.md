# 39-Bus System Parameters

This document summarizes the main machine and converter parameters used in the reported modified IEEE 39-bus study.

## System Summary

| Item                            | Value                                                        |
| ------------------------------- | ------------------------------------------------------------ |
| Test system                     | Modified IEEE 39-bus system                                  |
| System base                     | 100 MVA                                                      |
| Nominal frequency               | 50 Hz                                                        |
| Resource composition            | Bus 39 remains a synchronous generator; buses 30–38 are modeled as GFM-IBRs |
| IBR buses                       | 30, 31, 32, 33, 34, 35, 36, 37, 38                           |
| IBR terminal voltage level      | 22 kV                                                        |
| Main transmission voltage level | 345 kV                                                       |
| Special voltage level           | Bus 12 at 230 kV                                             |

## Remaining Synchronous Generator at Bus 39

| Bus  | Base MVA | x_l   | r_a  | x_d   | x'_d  | x''_d | T'_do (s) | T''_do (s) | x_q   | x'_q  | x''_q | T'_qo (s) | T''_qo (s) | H (s) |
| ---- | -------- | ----- | ---- | ----- | ----- | ----- | --------- | ---------- | ----- | ----- | ----- | --------- | ---------- | ----- |
| 39   | 1000     | 0.300 | 0    | 0.200 | 0.060 | 0.010 | 7.000     | 0.003      | 0.190 | 0.080 | 0.030 | 0.700     | 0.005      | 50.00 |

## Common GFM-IBR Settings

| Parameter                              | Value  |
| -------------------------------------- | ------ |
| Droop coefficient K                    | 2840   |
| Voltage-loop integral gain Ki_Vreg     | 90     |
| Current-loop proportional gain Kp_Ireg | 11     |
| Current-loop integral gain Ki_Ireg     | 0      |
| Virtual inductance Lv                  | 0      |
| Virtual resistance Rv                  | 0      |
| Reactive power setpoint Q0             | 0 pu   |
| Filter inductance Lf                   | 3.2 mH |
| Filter capacitance Cf                  | 50 uF  |

## Bus-Wise GFM-IBR Parameters

| Bus  | J     | Dp    | Dq       | Kp_Vreg | P0 (MW) | Vref (pu) | Vline (kV) |
| ---- | ----- | ----- | -------- | ------- | ------- | --------- | ---------- |
| 30   | 0.810 | 5.0e7 | 291866.1 | 7.00    | 250.00  | 1.0499    | 23.0978    |
| 31   | 1.296 | 5.0e7 | 272990.3 | 6.60    | 520.81  | 0.9820    | 21.6040    |
| 32   | 1.296 | 8.0e7 | 273574.0 | 6.60    | 650.00  | 0.9841    | 21.6502    |
| 33   | 1.296 | 7.0e7 | 277215.8 | 5.50    | 632.00  | 0.9972    | 21.9384    |
| 34   | 1.296 | 6.0e7 | 281413.5 | 3.85    | 508.00  | 1.0123    | 22.2706    |
| 35   | 1.296 | 8.0e7 | 291727.1 | 6.60    | 650.00  | 1.0494    | 23.0868    |
| 36   | 1.296 | 7.0e7 | 295674.6 | 4.40    | 560.00  | 1.0636    | 23.3992    |
| 37   | 1.296 | 7.0e7 | 285639.0 | 4.40    | 540.00  | 1.0275    | 22.6050    |
| 38   | 1.296 | 7.0e7 | 285361.0 | 4.40    | 830.00  | 1.0265    | 22.5830    |

## Network Branch Data

All values are on the system base (100 MVA). Tap = — indicates a transmission line (no transformer). For transformer branches, the Tap column gives the off-nominal turns ratio. B denotes total line charging susceptance (pu); transformer branches have B = 0 (shown as —).

| From | To   | R (pu) | X (pu) | B (pu) | Tap   | Vnom (kV) |
| ---- | ---- | ------ | ------ | ------ | ----- | --------- |
| 1    | 2    | 0.0035 | 0.0411 | 0.6987 | —     | 345       |
| 1    | 39   | 0.0010 | 0.0250 | 0.7500 | —     | 345       |
| 2    | 3    | 0.0013 | 0.0151 | 0.2572 | —     | 345       |
| 2    | 25   | 0.0070 | 0.0086 | 0.1460 | —     | 345       |
| 2    | 30   | 0.0000 | 0.0181 | —      | 1.025 | 22        |
| 3    | 4    | 0.0013 | 0.0213 | 0.2214 | —     | 345       |
| 3    | 18   | 0.0011 | 0.0133 | 0.2138 | —     | 345       |
| 4    | 5    | 0.0008 | 0.0128 | 0.1342 | —     | 345       |
| 4    | 14   | 0.0008 | 0.0129 | 0.1382 | —     | 345       |
| 5    | 8    | 0.0008 | 0.0112 | 0.1476 | —     | 345       |
| 6    | 5    | 0.0002 | 0.0026 | 0.0434 | —     | 345       |
| 6    | 7    | 0.0006 | 0.0092 | 0.1130 | —     | 345       |
| 6    | 11   | 0.0007 | 0.0082 | 0.1389 | —     | 345       |
| 7    | 8    | 0.0004 | 0.0046 | 0.0780 | —     | 345       |
| 8    | 9    | 0.0023 | 0.0363 | 0.3804 | —     | 345       |
| 9    | 39   | 0.0010 | 0.0250 | 1.2000 | —     | 345       |
| 10   | 11   | 0.0004 | 0.0043 | 0.0729 | —     | 345       |
| 10   | 13   | 0.0004 | 0.0043 | 0.0729 | —     | 345       |
| 10   | 32   | 0.0000 | 0.0200 | —      | 1.070 | 22        |
| 12   | 11   | 0.0016 | 0.0435 | —      | 1.006 | 345       |
| 12   | 13   | 0.0016 | 0.0435 | —      | 1.006 | 345       |
| 13   | 14   | 0.0009 | 0.0101 | 0.1723 | —     | 345       |
| 14   | 15   | 0.0018 | 0.0217 | 0.3660 | —     | 345       |
| 15   | 16   | 0.0009 | 0.0094 | 0.1710 | —     | 345       |
| 16   | 17   | 0.0007 | 0.0089 | 0.1342 | —     | 345       |
| 16   | 19   | 0.0016 | 0.0195 | 0.3040 | —     | 345       |
| 16   | 21   | 0.0008 | 0.0135 | 0.2548 | —     | 345       |
| 16   | 24   | 0.0003 | 0.0059 | 0.0680 | —     | 345       |
| 17   | 18   | 0.0007 | 0.0082 | 0.1319 | —     | 345       |
| 17   | 27   | 0.0013 | 0.0173 | 0.3216 | —     | 345       |
| 19   | 33   | 0.0007 | 0.0142 | —      | 1.070 | 22        |
| 19   | 20   | 0.0007 | 0.0138 | —      | 1.060 | 345       |
| 20   | 34   | 0.0009 | 0.0180 | —      | 1.009 | 22        |
| 21   | 22   | 0.0008 | 0.0140 | 0.2565 | —     | 345       |
| 22   | 23   | 0.0006 | 0.0096 | 0.1846 | —     | 345       |
| 22   | 35   | 0.0000 | 0.0143 | —      | 1.025 | 22        |
| 23   | 24   | 0.0022 | 0.0350 | 0.3610 | —     | 345       |
| 23   | 36   | 0.0005 | 0.0272 | —      | 1.000 | 22        |
| 25   | 26   | 0.0032 | 0.0323 | 0.5130 | —     | 345       |
| 25   | 37   | 0.0006 | 0.0232 | —      | 1.025 | 22        |
| 26   | 27   | 0.0014 | 0.0147 | 0.2396 | —     | 345       |
| 26   | 28   | 0.0043 | 0.0474 | 0.7802 | —     | 345       |
| 26   | 29   | 0.0057 | 0.0625 | 1.0290 | —     | 345       |
| 28   | 29   | 0.0014 | 0.0151 | 0.2490 | —     | 345       |
| 29   | 38   | 0.0008 | 0.0156 | —      | 1.025 | 22        |
| 31   | 6    | 0.0000 | 0.0250 | —      | 1.000 | 22        |

## Additional Notes

- The system is configured as a modified IEEE 39-bus benchmark in which Bus 39 remains the synchronous generator and buses 30–38 are modeled as GFM-IBRs.
- This document summarizes the main machine and converter settings used for the reported case study.
