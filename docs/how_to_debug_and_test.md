# How to Debug and Test Teal

##Pycharm

If you are running pycharm as your IDE download the algoDEA plugin
https://algodea-docs.bloxbean.com/
https://plugins.jetbrains.com/plugin/15300-algodea-algorand-integration

The tutorial on the algoDEA website has a really great overview of the tools included within 

1. Compile your pyteal program to a valid .teal format
2. Use AlgoDEA to generate a dry-run dump json of the transaction you're interested in testing
3. run `tealdbg debug <PROGRAM.teal> --dryrun-req <DRYRUN-DUMP.json>`

```
Note: if you are using sandbox you must copy the files into algod sandbox,
enter the docker and when calling tealdbg you must run with the additional parameter --listen 0.0.0.0

EX: tealdbg debug --listen 0.0.0.0 <PROGRAM.teal> --dryrun-req <DRYRUN-DUMP.json>
```
4. From here, open a chrome browser and navigate to chrome://inspect
```
Note: If this is your first time debugging you will need to click the configure button and add
localhost:9392 or 127.0.0.1:9392
```
5. Under Remote Target you should see "Algorand TEAL program", click the inspect link
6. This should open a debugger interface that most developers would be familar with
```
Note: if you do not see source code you may need to click the first item on the call stack
```