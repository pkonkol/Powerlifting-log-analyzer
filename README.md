# Open powerlifting Log
Open Powerlifting Log is a tool for efficient logging and analyzing training programs. It was
designed especially for RPE based programming, but might be used with oldschool
1RM percentage programs.





# How to use

## Planned exercise syntax
```
    Exercise [modifiers]: [Set#1] ... [Set#N]
```
Example | Description
------- | -----------
Comp SQ: x5@7 x5@8 x5@9 |
Comp BP w/slingshot : x3@9 |

### Modifiers syntax
Example | Description
------- | -----------
w/wraps | WITH/(modifier), should be used for equipment used during exercise
wo/belt | WITHOUT/(modifier), should be used for equipment not used during exercise
t/3111 | TEMPO/(\d{4}), tempo using 4 digits, seconds at: lowering, bottom, lifting, top
p/lowPause | PATTERN/(movementPattern), used as movement pattern modification

### Planned sets syntax
Example | Description
------- | -----------
x5@9 | Reps at RPE
3x5@90% | Sets x reps at percentage of weight from last set (load drop)
80%x5 | Percentage of 1RM x reps
x5@7@8@9 | Multiple sets x same amount of reps, in one string
3x5@7 | Sets x reps, first set on given RPE
4x@9 | Sets at RPE, reps vary by each set
160@9 | Weight at RPE, reps autoregulated


## Sets done syntax
Example | Description
------- | -----------
200@9 | Weight at RPE, presumed set numer corresponding to planned
200x5@9 | Weight x reps at RPE
160x5@7@8@8,5@9 | Weight x reps at RPE, multiple sets in one string
200@8@9,5@10 | Weight at RPE, presumed same set number and reps as planned


## Microcycle syntax

| D1 | [date] | D2 | [date] | ...|
| -- | ------ | -- | ------ | -- |
| Exercise#1 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | Exercise#1 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | ... |
| Exercise#2 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | Exercise#2 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | ... |


## Mesocycle syntax

| Mesocycle: [name] | | |
| ----------------- |-|-|
| W1 | | |
| [date] | | |
