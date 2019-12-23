# Powerlifting Log Analyzer
Open Powerlifting Log is a tool for efficient logging and analyzing training programs. It was
designed especially for RPE based programming, but might be used with oldschool
1RM percentage programs. Syntax is made to be concise, allowing one to quickly
and easily write trainings logs abundant in information.


# Usagee

## run.py syntax
```
python run.py -i <source spreadsheet> [-u {kg|lbs}]
```

##Exercise syntax
```
    Exercise [modifiers]: [Set#1] ... [Set#N]
```
Example | Description
------- | -----------
Comp SQ: x5@7 x5@8 x5@9 |
Comp BP w/slingshot : x3@9 |

###Basic syntax
Weight | {<float:weight>{kg|lbs|}|BW}
RPE | {{5|5.5|6|...|10}|9.(3)|9.(6)}
1RMpercentage | 0-100.0

### Exercise modifiers syntax
Syntax | Example | Description
------ | ------- | -----------
`w/<modifier>` | w/wraps | WITH/(modifier), should be used for equipment used during exercise
`wo/<modifier>` | wo/belt | WITHOUT/(modifier), should be used for equipment not used during exercise
`t/<int:tempo>` | t/3111 | TEMPO/(\d{4}), tempo using 4 digits, seconds at: lowering, bottom, lifting, top
`p/<movement_pattern>` | p/lowPause | PATTERN/(movementPattern), used as movement pattern modification

### Planned sets syntax
Scheme | Example | Description
------ | ------- | -----------
`x<reps>@<rpe>` | x5@9 | Reps at RPE
`<sets>x<reps>@<load_drop>` | 3x5@90% | Sets x reps at percentage of weight from last set (load drop)
`<1RMpercentage>%x<reps>` | 80%x5 | Percentage of 1RM x reps
`x<reps>(@<rpe>)+` | x5@7@8@9 | Multiple sets x same amount of reps, in one string
`<sets>x<reps>@<rpe>` | 3x5@7 | Sets x reps, first set on given RPE
`<sets>x@<rpe>` | 4x@9 | Sets at RPE, reps vary by each set
`<weight>@<rpe>` | 160@9 | Weight at RPE, reps autoregulated
`<weight>x<reps>` | 150KGx5 |#
`<sets>x<reps>` | 3x8 |#

## Sets done syntax
Scheme | Example | Description
---|------- | -----------
`<weight>@<rpe>` | 200@9 | Weight at RPE, presumed set numer corresponding to planned
`<weight>x<reps>@<rpe>` | 200x5@9 | Weight x reps at RPE
`<weight>x<reps>(@<rpe>)+` | 160x5@7@8@8,5@9 | Weight x reps at RPE, multiple sets in one string
`<weight>@<rpe>` | 200@8@9,5@10 | Weight at RPE, presumed same set number and reps as planned
`<sets>x<reps>/<weight>` | 3x10/20kg | ""
`<reps>x<weight>` | 10x100kg | ""
`X` | X | No sets were done
`V` | V | Exercise done as planned
`(<reps>,)+@<weight>` | 5,5,4,4,3@BW | Varied number of reps at given weight

## Superset syntax
Exercise planned column scheme | Example | Description
------ | ------- | -----------
`<exercise_name> (& <exercise_name>)+ : <planned_sets> (& <planned_sets>)+` | Lateral raise & leg raise: 3x8 & 3x12 | ""
`<exercise_name> (& <exercise_name>)+ : <planned_sets>` && | Lateral raise & leg raise: 3x12 && | The same planned sets scheme will be applied to both exercises
Sets done column scheme | Example | Description
------ | ------- | -----------
`<sets_done> (& <sets_done>)+ `| 2x8/20kg 8x15kg & 3x8/100kg | ""
`<sets_done> && | 3x8/20kg` && | The same done sets will be applied to both exercises




## Microcycle syntax

| D1 | <date> [@ <place>] | D2 | <date> [@ <place>] | ...|
| -- | ------ | -- | ------ | -- |
| Exercise#1 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | Exercise#1 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | ... |
| Exercise#2 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | Exercise#2 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | ... |


## Mesocycle syntax

| Mesocycle: [name] | | |
| ----------------- |-|-|
| W1 | | |
| [date] | | |

