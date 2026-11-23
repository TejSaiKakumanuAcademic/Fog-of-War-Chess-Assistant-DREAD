#Note: ctrl+f and find (!) for to-dos
#(*)denotes functions & classes which import or export values
#(T)denotes to-do for Tej; these are usually stand-in classes that need some of tej's classes put in, instead.

#For the sake of visualization, the code follows the following flow:

    #INPUT
######
    #ARITHMETIC
######
    #OUTPUT
######
    #TEST DATA




"""
deception_scorer.py Authored by Devlin Tracey 
No AI was used in the construction of this program.
FAKE TEST DATA IS CURRENTLY IMPLEMENTED AND MUST BE REMOVED FOR A WORKING PROGRAM

This program looks at each move DREAD might suggest and asks: after this move, is the opponent more confused or less confused about where our pieces are? It gives each move a number. positive means the opponent is more lost, negative means they’ve figured out more, and zero means nothing changed. If the information it gets is broken or incomplete, it refuses to make up a number.


LAYOUT: INPUT, then [CODE], then OUTPUT
    TOP:      the INPUT end (female, the sockets). Tej's classes plug in here, in Step 2.
    MIDDLE:   the CODE. All the arithmetic.
    BOTTOM:   the OUTPUT end (male, the plug). DeceptionResult, which goes out to the Move Ranker.
    Under that is the TEST BENCH. It runs on fake data and gets deleted when we're done.


    This program takes in 3 inputs and produces 5 outputs:
    There are three(3) INPUTS. These three inputs come from the UncertaintyResult class in the opponent_uncertainty_counter.py file. UncertaintyResult itself is arithmetic with inputs from FowEngine.py
        candidate_move          A string. An example would be 'g1f3'
        calculation_status      A string of three possible values: 'estimated' , 'incomplete' , 'invalid'. Invalid is the exception handler.
        scenario_measurements   Articulated as (before , after) , this counts how many boards the opponent has in its memory, versus how many it has after its been deceived.
                                An example of this is (40 , 20) It initially had 40 boards, and now has 20. This means the opponent has become more certain.
                                Another is (20, 40) It initialls had 20 boards, and now has 40. This means the opponent has become more confused.

    There are five(5) OUTPUTS that will be returned out of this 
        candidate_move          This is the move that was taken in. It remains unchanged.
        deception_score         This is an int that ranks the 'amount of deception achieved'. The math is described down below.
        scenario_count          This is how many scenarios went into the score. This is calculated by measuring the len(pairs) which itself is called later down.
        calculation_status      The final status of the arithmetic; can be:  "ok", "incomplete" or "invalid" where invalid is an exception handler.
        reason                  Displays what the problem is if anything comes back as invalid or otherwise wrong. This will be, effectively, part of debugging.

    The math:
        One scenario:   D = log2(after / before)    (this is the math tony provided)
                        above 0 means the opponent is less sure after our move,
                        below 0 means more sure, 0 means no change
        One move:       the plain average of D over all of its scenarios





STEPS
    INPUT END (the sockets)
        Step 1.  Import the libraries we need
        Step 2.  TEJ PUT YOUR CLASSES HERE (fake stand-ins until then)
        Step 3.  Name the input fields and the statuses we accept
    THE CODE (the arithmetic)
        Step 4.  Check that a pair of board counts is usable
        Step 5.  Score one scenario
        Step 6.  Score one candidate move
        Step 7.  Score every candidate move
    OUTPUT END (the plug)
        Step 8.  Define the output
    TEST BENCH (fake data, delete when done)
        Step 9.  Fake-input tests
        Step 10. Run the tests when this file is run directly
"""




##########################################################################################
################################ INPUT END (THE SOCKETS) #################################
####################################  STEPS 4-7  #########################################
##########################################################################################


####Step 1. Import the libraries we need####
import math                                             #Imports math lib, for log2() and fsum()
from dataclasses import dataclass                       #Imports dataclass for simple data holders
from typing import Optional                             #Improted so we an make ints/etc "a number or None"





####Step 2. TEJ PUT YOUR CLASSES HERE####(T)

###PLUG IN LINE 86###

###PLUG IN LINE 86###


#(!)#
###THIS IS SYNTHETIC DATA###
###STAND-INS FOR TEJ'S CLASSES. DELETE BOTH ONCE THE IMPORT LINE ABOVE IS ON###
###THEY DO NOT TO BE REPLACED, THESE TWO BLOCKS BELOW LITERALLY ONLY NEED DELETING / COMMENTING OUT###
@dataclass(frozen=True)                                 #Tells Python to automatically build the setup code for the class below, ScenarioMeasurement. @ is a decorator; it sats 'take the thing right below me, run it through this tool, and keep whatever comes back' Here it is telling ScenarioMeasurement to hold onto whatever before & after ints it gets after it gets some. frozen = true also locks them after stored
class ScenarioMeasurement:                              #(T)STAND-IN FOR TEJ'S ScenarioMeasurement (same name, same two fields). This class will be used to store the board counts. REMINDER: Higher board counts equal higher deception score. In other words, to get a higher deception score BEFORE < AFTER and vice versa
    before: int                                         #Boards the opponent could believe before our move
    after: int                                          #Boards the opponent could believe after our move


@dataclass(frozen=True)                                 #Ditto as earlier, 'hold on to what you get'
class UncertaintyResult:                                #(T)STAND-IN FOR TEJ'S UNCERTAINTYRESULT CLASS INSIDE OF OPPONENT_UNCERTAINTY_COUNTER.PY (same name, and the three fields we use). Declaring variables that will later be used to calculate THE DIFFERENCE BETWEEN THE BEFORE AND AFTER OF MOVES, COURTESY OF OMINOUS
    candidate_move: str                                 #The move being scored, in UCI text
    calculation_status: str                             #"estimated", "incomplete" or "invalid"
    scenario_measurements: tuple = ()                   #The (before, after) pairs, one per scenario. TUPLES ARE MIXED LISTS. TUPLES are a 'open-array' meaning an array with a size you can define, whether its 2-tuple, 3-tuple or 10-tuple.





####Step 3. Name the input fields and the statuses we accept####
INPUT_MOVE = "candidate_move"                           #(*)SOCKET 1. The name of the move field inside Tej's UncertaintyResult. If Tej ever renames a field, change it HERE and nowhere else
INPUT_STATUS = "calculation_status"                     #(*)SOCKET 2. The name of the status field
INPUT_PAIRS = "scenario_measurements"                   #(*)SOCKET 3. The name of the (before, after) pairs field
USABLE_STATUSES = {"estimated", "exact"}                #A variable that holds the counter statuses we accept: "estimated" and "exact". If a result's status is on this list, it is complete enough to score. (NOTE: tej counter only returns "estimated" 11/15)




##########################################################################################
################################  ARITHMETIC BLOCKS  #####################################
#################################  STEPS 4 - 7  ##########################################
##########################################################################################


####Step 4. Check that a pair of board counts is usable####
def _validate_counts(before, after):                                          #THIS IS AN ERROR HANDLER
    for name, value in (("before", before), ("after", after)):                #Iterates through the pairs...
        if isinstance(value, bool) or not isinstance(value, int):             #If it's not boolean or an int (in other words, not a whole number)
            return False, f"{name} count is not a whole number: {value!r}"    #Return false and a message
        if value <= 0:                                                        #If the value is a zero or less...
            return False, f"{name} count must be above zero: {value}"         #Return false and a message
    return True, ""                                                           #OTHERWISE, both counts are usable


#NOTE: FUNCTIONS ALWAYS DO WHATS BELOW IMMEDIATELY BELOW THEM IN PYTHON (duh)
def _pair_counts(pair):                                                       #This takes in ScenarioMeasurement from Tej's py. It holds .before and .after. It will then return pair_counts with two variables inside it, before and after. This will be the 
    if hasattr(pair, "before") and hasattr(pair, "after"):                    #hasattr asks if the pair has before & after
        return pair.before, pair.after                                        #If it does it reads the two fields
    before, after = pair                                                      #Otherwise treats it as a plain (before, after) tuple
    return before, after                                                      #Returns em both





####Step 5. Score one scenario####
def score_scenario(before, after):                      #Scores one scenario: D = log2(after / before)
    ok, reason = _validate_counts(before, after)        #Checks the counts first
    if not ok:                                          #If either count is unusable...
        raise ValueError(reason)                        #...throw a flag
    return math.log2(after / before)                    #Positive results mean the opponent is less sure (good) while negative results mean the enemy is more sure (bad)





####Step 6. Score one candidate move (this is where the inputs are taken in)####
#NOTE: DeceptionResult is declared at the bottom (Step 8, the OUTPUT end). Python only needs it to exist when this function RUNS, not when it's declared
def score_candidate(result):                                                                       #(*)TAKES IN 'result', which is a variable from opponent_uncertainty_counter.py from UncertaintyResultopponent_uncertainty_counter.py frmo UncertaintyResult

    move = getattr(result, INPUT_MOVE, "?")                                                        #(*)Makeks a new variable called move, and stores whatever is on the right in it. getattr is a builtin python function that looks inside of object for a field by name. Result is the object that is beeing looked inside, this is from tej's uncertaintyresultl in his opponent_uncertainty_counter.py. The field that is grabbed frmo inside that object is 'candidate_move' I made a backup, denoted by '?' since it was crashing without it. Inshort, this function grabs candidate_move frmo the object. (The field name now comes from INPUT_MOVE in Step 3)

    status = getattr(result, INPUT_STATUS, "invalid")                                              #(*)Ditto. Reaches into tej's opponent_uncertainty_counter.py and grabs the object 'result' from the calculation_status field, which itself is in the UncertaintyResult class in tej's py file. (The field name now comes from INPUT_STATUS in Step 3)

    pairs = tuple(getattr(result, INPUT_PAIRS, ()) or ())                                          #Pairs is a variable that looks inside 'result' from 'scenario_measurements'. () creates an empty list because it was freaking out without one, ditto for the second (). TUPLE TURNS THE RETURN INTO A TUPLE, WHICH IS A FIXED LIST(**). The tuple can be counter with len(). Will be looped over(!). (The field name now comes from INPUT_PAIRS in Step 3)
    count = len(pairs)                                                                             #Declares count, which'll be the amount of pairs (scenarios)
    if status == "incomplete":                                                                     #The counter ran out of time or positions
        return DeceptionResult(move, None, count, "incomplete", "counter result is incomplete")    #DECLARES the funcction to output a DeceptionResult with no score when the counter result is incomplete. (IMPORTANT!) This is one of the outputs returned to the caller, planned to be Ethan's analysis_worker.py
    if status not in USABLE_STATUSES:                                                              #Any other status we cannot trust ("invalid" or unknown)
        return DeceptionResult(move, None, count, "invalid", f"counter status is {status!r}")      #CHECKS the status from tej's counter against USABLE_STATUSES. If it is not "estimated" or "exact", we don't trust it, so we stop here and send out no-score (we wont work with it)
    if count == 0:                                                                                 #If there is no scenarios...
        return DeceptionResult(move, None, 0, "invalid", "no scenarios")                           #...then no score

    scores = []                                                                                    #Will hold one score per scenario
    for pair in pairs:                                                                             #(*)AS LONG AS THERE IS A PAIR
        try:                                                                                       #Tries to score this scenario
            before, after = _pair_counts(pair)                                                     #Gets the two counts out of the pair
            scores.append(score_scenario(before, after))                                           #Adds this scenario's delta (change) to the list 
        except (ValueError, TypeError) as problem:                                                 #A count was unusable, or the pair has a missing parameter
            return DeceptionResult(move, None, count, "invalid", str(problem))                     #Throw an error and yell at the user angrily

    average = math.fsum(scores) / count                                                            #Averages all the scores
    return DeceptionResult(move, average, count, "ok")                                             #Returns the score, LIKELY BACK TO TEJ'S CLASS

#NOTE: THESE ARE DECLARATIONS AND ARE TO BE USED FURTHER DOWN.




####Step 7. Score every candidate move####
def score_candidates(results):                                #Creates a space for the scores
    return [score_candidate(result) for result in results]    #Brings in the result (one at a time)




##########################################################################################
#################################  OUTPUT  ###############################################
##########################################################################################


####Step 8. Define the output####
@dataclass(frozen=True)                                 #Ditto as earlier
class DeceptionResult:                                  #(*)Defines class DeceptionResult. This is the blank form that score_candidate will fill in, once per move. THIS IS WHAT GOES OUT to the Move Ranker
    candidate_move: str                                 #The move that was scored
    deception_score: Optional[float]                    #The score
    scenario_count: int                                 #How many scenarios went into the score
    calculation_status: str                             #"ok", "incomplete" or "invalid"
    reason: str = ""                                    #For debug, if it stops working




##########################################################################################
##########################TEST BENCH (FAKE DATA, DELETE WHEN DONE)########################
##########################################################################################


#(!)#
###SYNTHETIC TEST RESULTS THESE ARE FAKE####


###DELETE STEPS 9 - 10 WHEN READY TO GO###


####Step 9. Fake-input tests####
def _fake(move, pairs, status="estimated"):                                                                                                                        #Builds a fake counter result from plain (before, after) pairs
    return UncertaintyResult(candidate_move=move, calculation_status=status, scenario_measurements=tuple(ScenarioMeasurement(b, a) for b, a in pairs))             #WRAPS each pair as a ScenarioMeasurement. Fills the fields BY NAME so it also works with Tej's real class, which has extra fields


def _close(value, target):                                                                                                                                         #ERROR HANDLER FOR OUT OF BOUNDS
    return value is not None and abs(value - target) < 0.0005                                                                                                      #If its less than 0.0005, then freak out and crash

#(!)#
####THREE TEST SETS! COMMENT THESE OUT WHEN DONE!####
def run_fake_tests():                                                                                                                                              #FUNCTION (not a class) that runs every fake test below, prints PASS or FAIL for each one, then prints a small demo. Step 10 calls this when the file is run directly. It runs on the FAKE data from Step 2, so COMMENT IT OUT once Tej's real classes are plugged in
    checks = []                                                                                                                                                    #A list that will hold the OUTCOME of every test as (test name, passed?). Starts empty and gets filled by every checks.append below. The PASS/FAIL printout reads from it at the end
    abc = [(40, 20), (60, 90), (100, 200)]                                                                                                                         #Three scenarios, each one a (before, after) board count. This is Anthony's three-scenario test set
#Take a breath this is gonna be rough

    r = score_candidate(_fake("g1f3", [(100, 200)]))                                                                                                               #BUILDS a fake result for move g1f3 (a real chess move, the knight from g1 to f3, used here as a stand-in) with ONE scenario: 100 boards before, 200 after. SCORES it with score_candidate and stores the finished DeceptionResult in r
    checks.append(("100 -> 200 gives +1.000", _close(r.deception_score, 1.0)))                                                                                     #SAVES this test to checks as (name, passed?). It passes if the score is within 0.0005 of +1.000. 100 boards to 200 is TWICE as many boards, so the opponent is twice as unsure, and log2 of 2 is 1

    r = score_candidate(_fake("g1f3", [(100, 50)]))                                                                                                                #Same setup, but the opponent goes from 100 boards to 50
    checks.append(("100 -> 50 gives -1.000", _close(r.deception_score, -1.0)))                                                                                     #Passes if the score is within 0.0005 of -1.000. HALF as many boards means the opponent is twice as SURE (bad for us), and log2 of 0.5 is -1

    r = score_candidate(_fake("g1f3", [(100, 100)]))                                                                                                               #Same setup, but nothing changes: 100 boards before, 100 after
    checks.append(("100 -> 100 gives 0.000", _close(r.deception_score, 0.0)))                                                                                      #Passes if the score is within 0.0005 of 0.000. Nothing gained or lost, and log2 of 1 is 0

    r = score_candidate(_fake("g1f3", abc))                                                                                                                        #Scores ALL THREE scenarios in abc as one move. Each scenario gets its own score, then the three get averaged
    checks.append(("three scenarios average +0.195", _close(r.deception_score, 0.195)))                                                                            #Passes if the average is within 0.0005 of +0.195.

    r = score_candidate(_fake("g1f3", [(0, 100)]))                                                                                                                 #A zero count: 0 boards before, 100 after. Board counts can't be zero (no dividing by 0, no log of 0)
    checks.append(("0 -> 100 is invalid", r.calculation_status == "invalid" and r.deception_score is None))                                                        #Passes only if BOTH are true: the status is "invalid" AND the score is None. It must refuse to score, never make up a number

    r = score_candidate(_fake("g1f3", [(-5, 100)]))                                                                                                                #A negative count: -5 boards before. Boards can't be negative
    checks.append(("-5 -> 100 is invalid", r.calculation_status == "invalid"))                                                                                     #Passes if the status is "invalid" (a bad count means the whole move gets rejected)

    r = score_candidate(UncertaintyResult(candidate_move="g1f3", calculation_status="estimated", scenario_measurements=(ScenarioMeasurement(100, "unknown"),)))    #Built BY HAND instead of with _fake, because _fake only takes numbers. The after count is the TEXT "unknown" instead of a number. The trailing comma after the ScenarioMeasurement is what makes it a 1-item tuple
    checks.append(("100 -> 'unknown' is invalid", r.calculation_status == "invalid"))                                                                              #Passes if the status is "invalid". Wrong data type gets rejected

    r = score_candidate(_fake("g1f3", [(100, 200)], status="incomplete"))                                                                                          #A fake result with the status set to "incomplete": the counter ran out of time or positions
    checks.append(("incomplete status gives no score", r.calculation_status == "incomplete" and r.deception_score is None))                                        #Passes only if the status is "incomplete" AND the score is None. An incomplete result never gets a score

    r = score_candidate(_fake("g1f3", []))                                                                                                                         #An empty list: NO scenarios at all
    checks.append(("no scenarios is invalid", r.calculation_status == "invalid" and r.deception_score is None))                                                    #Passes only if the status is "invalid" AND the score is None. Nothing to average, so no score AAAAAAAAAAA

    forward = score_candidate(_fake("g1f3", abc)).deception_score                                                                                                  #Scores abc in the normal order and keeps ONLY the score (.deception_score)
    backward = score_candidate(_fake("g1f3", list(reversed(abc)))).deception_score                                                                                 #Same three scenarios in REVERSE order. reversed() flips them, list() turns the flipped result back into a list
    checks.append(("reversed order gives the same score", forward == backward))                                                                                    #Passes if both scores are EXACTLY equal. Order must not matter (math.fsum in Step 6 is what guarantees this)

    runs = {score_candidate(_fake("g1f3", abc)) for _ in range(10)}                                                                                                #Scores the same input 10 times and drops the 10 results into a SET (a group with no repeats). The _ is a throwaway name since we don't need the loop counter. DeceptionResult being frozen is what lets results go in a set
    checks.append(("10 runs give the same output", len(runs) == 1))                                                                                                #Passes if the set holds exactly ONE item, meaning all 10 results were identical

    r = score_candidate(UncertaintyResult(candidate_move="g1f3", calculation_status="estimated", scenario_measurements=((100, 200),)))                             #Built by hand with a PLAIN tuple (100, 200) instead of a ScenarioMeasurement. Tests the plain tuple path in _pair_counts, the part that unpacks a pair into before and after
    checks.append(("plain (before, after) tuples plug in too", _close(r.deception_score, 1.0)))                                                                    #Passes if it still scores +1.000. Both shapes fit the socket

    for name, passed in checks:                                                                                                                                    #Goes through every outcome in checks one at a time. name is the test name and passed is True or False
        print(("PASS  " if passed else "FAIL  ") + name)                                                                                                           #Prints PASS or FAIL, then the test name. The part in parentheses picks which word to print, based on whether the test passed

    print()                                                                                                                                                        #Prints a blank line to separate the test results from the demo
    print("Demo: three candidate moves (Anthony's example, opponent starts at 100 boards)")                                                                        #Prints the demo heading
    demo = score_candidates([_fake("g1f3", [(100, 160)]), _fake("e2e4", [(100, 80)]), _fake("f1c4", [(100, 125)])])                                                #Scores THREE different moves at once with score_candidates (Step 7): g1f3 goes from 100 boards to 160, e2e4 goes from 100 to 80, and f1c4 goes from 100 to 125. Gives back a list of three DeceptionResults
    for d in demo:                                                                                                                                                 #Goes through each scored move. Each d is one DeceptionResult
        print(f"  {d.candidate_move}: {d.deception_score:+.3f}  ({d.calculation_status})")                                                                         #Prints the move, its score and its status. The part after the colon inside the curly braces makes it always show a plus or minus sign and 3 decimal places

    return all(passed for _, passed in checks)                                                                                                                     #Hands back True ONLY if EVERY test passed (all() is False if even one is False). The _ ignores the test name. Step 10 turns this into the exit code





####Step 10. Run the tests when this file is run directly####
if __name__ == "__main__":                              #Only do anything when THIS py file is called because if I don't put this in here it'll find a way to do it just to spite me
    all_passed = run_fake_tests()                       #Then run the fake tests
    raise SystemExit(0 if all_passed else 1)            #Code 0 if pass, 1 if not
