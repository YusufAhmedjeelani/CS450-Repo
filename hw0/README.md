# Homework 0: Intro to Python and Git


This assignment has the following purposes:

## [Setup](https://drive.google.com/file/d/1qasz_FSLj5K36VnlAOJES-jkIHRgSbKJ/view?usp=sharing) 

  1. Strictly use python 3.10 for all of yours assignments, since same version will be used with autograder.
  2. Make sure your github account is associated with uic email id, setup the ssh keys.


## Introduction to Python

If you're unsure what version of python you are using, you can always check
by typing `python --version` on the command line.

Python is a popular, dynamic, memory managed language.  It has many features
that make it easier to work with than other languages.
If you're already familiar with python, feel free to
skip over this section.  For those new to the language, this section
provides an overview of some of the unique features of the language.

## Python Basics

### Syntax
If you're used to languages like C and Java, python might look a little alien.
This is because python does not use curly braces (`{` or `}`) to denote
the end of blocks, or semi-colons to denote the end of lines.  Instead, Python
relies on white space.

```c
// In C you end up repeating yourself a lot, indenting things and wrapping
// blocks in curly braces.
void a_function(int * firstArg, int * secondArg) {
    // You also repeat yourself, but using both ";" and new lines
    // to mark the end of a line of code.
    int firstInt = 1;
    int secondInt = 2;
}
```

```python
# In Python, you type less, and have less redundancy.  You
# may find that this reduces the number of errors you make, and makes
# your programs easier to maintain.
def a_function(first_arg, second_arg):
    first_int = 1
    second_int = 2
```

### Dynamic Types
Languages like Java and C require you to declare types in function signatures
and variable declarations.  If, for example, you're writing a program C, you
and you want to declare a variable to be an integer, and another variable to
be a character, you need to do something like the following:

```c
#include <stdio.h>

// Defining some variables in C
int myInt = 3;
char someChar = 'a';

// Defining a function in C
int some_function(int anInt, char aChar) {
    printf("Here is the integer I was given: %d\n", anInt);
    printf("And here is the character I was given: %c\n", aChar);
    return 0;
}

// C programs always start with the main function
int main(int argc, char * argv[]) {
    // Calling a function in C
    some_function(myInt, someChar);
}
```

In most ways, python is much less strict about types.  You don't specify a
type when you declare a variable, and variables can take on values of any type,
even changing over the lifetime of your program.  The below, for example,
is valid python code:

```python
# Defining some variables in python.  Note that we don't define any
# types, python does that automatically.
my_int = 3
some_char = "a"

# Defining a function in python.  Note that you don't declare types
# for the arguments in python, the language handles that for you.
# We also don't have to declare a return type, thats handled automatically
# too.
def some_function(an_int, a_char):
    print("Here is the integer I was given:", an_int)
    print("And here is the character I was given:", a_char)

some_function(my_int, some_char)
```

### Native Data Structures
Python provides many conveniences for defining and working with data structures
compared to languages like Java and C.  Python doesn't
allow you to do anything you can't do in Java and C, Python makes it much
easier, and much less error prone, to interact with structures like arrays
(which python calls *lists*), hash tables (which python calls *dicts*), and
sets (which python calls... *sets*).

```python
# In python, you can define an array (or, in python terms, a list) of
# variables in line, and then loop over them easily.  The below code
# creates a list / array of three strings, and then prints them all out.
list_of_strings = ["first", "second", "third"]

# Python provides this short hand syntax for iterating over each element
# in a list.  In C, you might use a for loop and index into each element
# in the list.
#
# The below list will print out the following text:
#
#   first
#   second
#   third
for a_string in list_of_strings:
    print(a_string)

# We can do the same thing with a hash table, or a mapping of values
# to values.  The below code maps the names of numbers (as strings) to
# their actual value (as integers).
number_mapping = {
    "one": 1,
    "two": 2,
    "three": 3,
}

# Now we loop over each item in the hash table (or dict) we created,
# which will produce the following lines (though the order is
# unpredictable).
#
#   one can also be written as 1
#   two can also be written as 2
#   three can also be written as 3
for string_version, int_version for number_mapping.items():
    print(string_version, "can also be written as", int_version)
```

### Large Standard Library
Python comes with a large standard library, and includes "out of the box"
a large amount of functionality to help you complete common tasks.
This is true compared to Java, and *especially* compared to C. This reduces the
amount of third party code you need in Python to complete common tasks.

A full list of all the functionality included in the
[python standard library](https://docs.python.org/3.10/library/index.html)
can be found online.

### Other Python Features
The above just scratches the surface of what makes python an interesting
and useful language.  Python has powerful object oriented tools like Java,
closures and anonymous functions like Lisp and JavaScript, and
a full module system for structuring your code and taking advantage of code
written by others.

You wont be using most of these features in this class,
but they're in the language and it will benefit you to learn more about them
as you become more familiar with the language.

### Writing Better Python
There are great tools to help you become a better python programmer, and to
help you write better, cleaner, less-bug-laden code.  Its highly recommended
that you use these tools, and they can help you catch, fix and prevent errors,
and write code that will be easier to understand if you ever need to revisit
them (plus, if you ever use any of these assignments as code samples in a job
application, its a good thing to show that you're familiar with and already
following python best practices.

One tool is [pep8](https://pep8.readthedocs.io/), a command
line tool that checks that your code is following python formatting and style
best practices.  Making that your code is well formatted will make it easier
to understand, revisit, revise, and help you avoid
[subtle errors](https://gotofail.com/).  You should check that your
code matches the `pep8` style wherever possible.

[pylint](https://www.pylint.org/) is another code quality tool.  It checks
that your code is well documented, well formatted, and avoids practices
that can make your code confusing and fragile.  You should also consider
using `pylint` to check all the python code you submit in this course.

For this assignment, using `pep8` and `pylint` is not required, just highly
recommended.  However, it may be required on future assignments.  Please
familarize yourself with these tools as soon as possible.

### Starter Files
* `hw0.py`: The source file you where you will be writing your code.
* `data`: A directory containing file(s) which you will be using for this assignment.


## <a name="assignment-section"></a>Assignment Tasks
Let's get started with the actual tasks that you will be writing for this assignment. You will only be making changes to `hw0.py` as this is the only submitted to the server for grading.

1. Modify the function `get_version` in `hw0.py` to return the version of python in the form of `3.x.x` . Make sure your return string is a single line and you remove any other details from your response.

2. Modify the function`alternative_sum` in `hw0.py` so that it takes in 2 integer arguments, `start`, `n` and returns a list generated by the following sequence:

    Using `start` as an initial number in the list, the function increments the list by adding a new element at the end of the list by summing the last and the third last element.  If the third last element is the list does not exist, the new element is generated by summing the last element to itself. The function returns the generated list once the length of the list reaches `n`. In addition, your function needs to checks for the following conditions:
    * `start` can only be a non zero positive number. If it is negative, the function should return an empty list.
    * `n` should be a number between 5 and 20, inclusive. If `n` is out of range, the function should return an empty list.
    
    For example if I call `alternative_sum(15, 5)` the function returns `[15, 30, 60, 75, 105]`. The list generation is performed as follows:
    ```
    [15] # initial list, only a single element so the new element is generated by summing the last element to itself.
    [15, 30] 
    [15, 30, 60] # the third last element exists, generate the new element by summing the last and the third last elements.
    [15, 30, 60, 75]
    [15, 30, 60, 75, 105] # final result that is returned.
    ```

3. The third task of the assignment deals with reading from a file. the `data` directory contains a file named `scores.csv`. Your goal in this task is to modify the function `order_scores` in `hw0.py` so that it returns the names in the form of a list which is sorted by their respective scores in ascending order. For example, `Shawn` has the lowest score so will be the first element of the returned list. 

### Hints
For *number 1*, do not hardcode the version of python into your code (i.e. do not write return("3.10")). You must use the python system for return the current version to receive credit. 
The `sys` module will be helpful. Also, depending on your environment, python might print your python version on more than one line. You can use the relevant 
[string methods](https://docs.python.org/3/library/stdtypes.html#string-methods) in python to achieve the required formatting of the response.

For *number 3*, there are a few ways you can read the file, the `csv` module will be helpful in this case. To make things easier for you, the scores in the file are unique.

## Submission and Logistics

- Clone your homework repository
- Write your code and make sure you can pass all test cases.
- When you are ready to sumit your homework, push it back to the repository for grading

```sh
git add . 
git commit -m "<add your comment here>" 
git push
```

Important Note:
Please do not add any print/echo statement anywere in your code. Your code will be evaluated by auto grader and it just checks the returned values from the functions. You are required to ONLY fill the functions. 
