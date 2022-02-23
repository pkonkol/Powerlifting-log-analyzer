# Powerlifting Log Analyzer
## Rewriting that from half-scratch with gspread and may finish this time
Powerlifting log analyzer is a tool for efficient logging and analyzing training programs. It was
designed especially for RPE based programming, but might be used with oldschool
1RM percentage programs. Syntax is made to be concise, allowing one to quickly
and easily write trainings logs abundant in information.


# Usage

## main.py
1. Set up gspread api credentials as in documentation
1. Set up your spreadsheets name and tab name in main.py
1. Run
```
python main.py
```
## tests
```
python tests/exercise.py
python tests/utils.py
```

### Exercise syntax
```
    Exercise [modifiers]: [Set#1] ... [Set#N]
```

Example |
------- |
Comp SQ: x5@7 x5@8 x5@9 |
Comp BP w/slingshot : x3@9 |

### Basic syntax
| | |
| - | - |
| Weight | {`<`float:weight> {kg &#124; lbs} &#124;BW}
| RPE | {5 &#124;5.5 &#124;6 &#124;... &#124;10 &#124;9.3 &#124;9.6}
| 1RMpercentage | `0-100.0`

### Exercise modifiers syntax
Syntax | Example | Description
------ | ------- | -----------
`w/<modifier>` | w/wraps | WITH/(modifier), should be used for equipment used during exercise
`wo/<modifier>` | wo/belt | WITHOUT/(modifier), should be used for equipment not used during exercise
`t/<tempo>` | t/3111 | TEMPO/(\d{4}), tempo using 4 digits, seconds at: lowering, bottom, lifting, top
`p/<movement_pattern>` | p/lowPause | PATTERN/(movementPattern), used as movement pattern modification

### Planned sets syntax
Scheme | Example | Description
------ | ------- | -----------
`<sets>x<reps>` | 3x8 | #
`<sets>x<reps>@<1RMpercentage>` | 3x5@80% | Sets x reps at percentage of weight from last set (load drop)
`<sets>x<reps>@<1RMpercentage>-<1RMpercentage>`%| 3x5@80-90%
`<reps>x<1RMpercentage>%` | 5x80% | Percentage of 1RM x reps
`x<reps>@<rpe>` | x5@9 | Reps at RPE
`x<reps>(@<rpe>)+` | x5@7@8@9 | Multiple sets x same amount of reps, in one string
`<sets>x<reps>^@<rpe>` | 3x5^@7 | Sets x reps, first set on given RPE
`x<reps>$@<rpe>` | x6$@9 | Ramp up until you reach set of 6 reps @9
`<sets>x<reps>V<load_drop>` | 3x5V90% | Sets x reps at percentage of weight from last set (load drop)
`x<reps>@<rpe>-<percent_fatigue>%` | x5@9-7% | Fatigue percentage - after main set at given RPE drop weight by given percents and repeat until rpe the same as main set
`<sets>x@<rpe>` | 4x@9 | Sets at RPE, reps vary by each set
`<weight>@<rpe>` | 160@9 | Weight at RPE, reps autoregulated
`<weight>x<reps>` | 150KGx5 |#
`<sets>x` | 5x | For simple supplemental work where you don't need to specify reps

## Sets done syntax
Scheme | Example | Description
---|------- | -----------
`<weight>@<rpe>` | 200@9 | Weight at RPE, presumed set numer corresponding to planned
`<weight>x<reps>@<rpe>` | 200x5@9 | Weight x reps at RPE
`<weight>x<reps>(@<rpe>)+` | 160x5@7@8@8,5@9 | Weight x reps at RPE, multiple sets in one string
`<weight>@<rpe>` | 200@8@9,5@10 | Weight at RPE, presumed same set number and reps as planned
`<`sets>x<reps>{x &#124;@ &#124;/} `<`weight> | 3x10/20kg | ""
`<reps>x<weight>` | 10x100kg | ""
`[Xx]` | x | No sets were done
`[V]` | V | Exercise done as planned (TODO generate all sets?)
`[v]{1,}` | vvvvv | As many sets as v's done (5 in the example)
`<weight>X[Vv]+` | 40kgXvvvv | As many sets as v's done with given weight (4 in the example)
`(<reps>,)+@<weight>` | 5,5,4,4,3@BW | Varied number of reps at given weight

## Superset syntax
Exercise planned column scheme | Example | Description
------ | ------- | -----------
`<exercise_name> (& <exercise_name>)+ : <planned_sets> (& <planned_sets>)+` | `Lateral raise & leg raise: 3x8 & 3x12` | ""
`<exercise_name> (& <exercise_name>)+ : <planned_sets> ` | `Lateral raise & leg raise: 3x12 ` | The same planned sets scheme will be applied to both exercises

Sets done column scheme | Example | Description
------ | ------- | -----------
`<sets_done> (& <sets_done>)+ `| `2x8/20kg 8x15kg & 3x8/100kg` | ""
`<sets_done> &&` | `3x8/20kg &&` | The same done sets will be applied to both exercises (TODO really?)



## Naming
**B\d+** for training **Block**
**M\d+** for training **Microcycle**
**S\d+** for training **Session**
## Microcycle syntax

| S1 | `<date> [@ <place>]` | S2 | `<date> [@ <place>]` | ...| GPP | -- |
| -- | ------ | -- | ------ | -- | -- | -- |
| Exercise#1 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | Exercise#1 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | ... | Bouldering | 01.02.03 18:00-20:00 |
| Exercise#2 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | Exercise#2 [modifiers]: [Set#1] ... [Set#N] | [Set\_done#1] ... [Set\_done#N] | ... | . | . |
| . | . | . | . | ... | . | . |
| . | . | . | . | ... | . | . |
| . | . | . | . | ... | . | . |


## Mesocycle syntax

| B1 [: name] | `<date_start>` | |
| ----------------- |-|-|
| M1 | Microcycle#1 ->
| [date] | \/
| . |
| . |
| . |
| M2 | Microcycle#2 ->
| [date] | \/
| . |
| . |
| . |
| `Mesocycle_end:` | `<date_end>`


