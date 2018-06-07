from subprocess import Popen, PIPE
from datetime import datetime, timedelta
from time import sleep
from matplotlib import pyplot as plt, dates
from os import path, system, walk
from zipfile import ZipFile, ZIP_DEFLATED
from sys import argv, exit as sysexit


def page_refresh():
    """Prints 'banner' with contact info at top of the terminal window."""
    system('cls')  # Clears terminal window.
    print('This network testing script was developed by End-to-End Service Analysis')
    print('For support, please contact Jeremy.Coombs@team.telstra.com\n')


def reset_session(runtime):
    """Used to reset back to menu() when user gives invalid arguments."""
    print('The session will now be reset.\n')
    sleep(1)
    menu(runtime)


def host_check(hostname):
    """Ensures that a host is responding to pings before performing a test."""
    check = Popen(['ping', '-n', '5', hostname], stdout=PIPE)  # Send 5 ICMP packets.
    checked = []
    for line in check.stdout:  # Save output of pings to list(checked)
        line = str(line).split()
        if len(line) > 4 and str(line[4])[:4] == 'time':  # If this appears in string, ping was successful.
            checked.append(line)  # Add to list for counting.
    if len(checked) > 0:  # At least 1 positive response saved in list(checked).
        return True
    else:  # No positive responses in the test. Host is not responding.
        sleep(1)
        return False


def test(hostname, runtime):
    """Establishes time to run tests and performs main testing loop."""
    filename = hostname + '.log'
    now = datetime.now()
    delta = timedelta(minutes=runtime)  # Timedelta sets time to run tests until.
    future = now + delta
    future_f = str(future.strftime("%H:%M, %d/%m/%y"))
    print('\nPinging {} until {}...' .format(hostname, future_f))
    while now < future:  # Continue to run ping() until time specified in timedelta:
        now = datetime.now()
        ping(hostname, filename, now)
        sleep(3)
    print('Done!')
    print('Generating graph...')
    graph(hostname)
    print('Test for {} complete!'.format(hostname))


def ping(host, filename, now):
    """Prints the current time, performs 10 pings, and records output to {host}.log file."""
    with open(filename, 'a+') as file:
        file.write('\n' + now.strftime("%H:%M:%S, %d/%m/%Y") + '\n')
    with open(filename, 'a') as file:
        Popen(['ping', '-n', '10', host], stdout=file).wait()


def graph(hostname):
    """Plots latency over time by reading {hostname}.log file."""
    filename = hostname + '.log'
    with open(filename, 'r') as f:  # Empty arrays to store data points.
        x = []  # Datetimes for latency.
        xt = []  # Datetimes for timeouts.
        y = []  # Latency.
        yt = []  # Timeouts.
        f.readline()  # Skips first line.
        while True:  # Collecting ping statistics.
            try:
                t = f.readline()
                raw = t[1:-1]  # Removed newline characters from 't'
                if t == 'Control-C\n':  # If user Control-C's, break to main loop.
                    f.readline()
                    break
                elif t == "Test statistics:\n":  # If this file has already been graphed, break to main loop.
                    break
                elif t == '':  # If empty line, break to main loop.
                    break
                tr = datetime.strptime(raw, "%H:%M:%S, %d/%m/%Y")  # Datetime stamp in .log file.
                tf = datetime.strftime(tr, "%Y %m %d %H %M %S")  # Split up datetime into 6 separated sections.
                run_time = datetime(*[int(j) for j in tf.split()])  # TODO: What does this line do?
            except TypeError:  # If invalid datetime given.
                break
            line = f.readline().split()  # Sometimes there will be a newline, this skips new lines.
            if len(line) == 0:
                line = f.readline().split()
            if line[0] == 'Pinging':  # If pinging.
                while True:
                    ping_time = 0
                    try:
                        t = f.readline()
                        s = t.split()  # Split data into list.
                        if len(s) == 6:  # Normal output of ping is 6 words long.
                            ping_time = int(s[4].replace('<', '=').split('=')[1][:-2])
                        elif len(s) == 4:  # But one of the log files was only 4 words.
                            ping_time = int(s[3].replace('<', '=').split('=')[1][:-2])
                        else:  # If not 4 or 6 words we don't know what to do.
                            raise IndexError
                    except IndexError:
                        if len(t.split()) == 0:  # If newline, ping is finished.
                            break
                        elif len(t.split()) == 3:
                            xt.append(run_time)
                            try:  # Use previous ping value to put a red dot on the ping graph.
                                yt.append(y[-1])
                            except IndexError:  # If no pings yet recorded, add timeout dot with latency 0.
                                yt.append(0)
                            continue
                    x.append(run_time)
                    y.append(ping_time)
                for _ in range(5):  # Skip five lines.
                    f.readline()
            elif line[0:2] == ['Ping', 'request']:
                f.readline()
                continue
            elif line[0:2] == ['Request', 'timed']:
                f.readline()
                continue
            else:  # Else who knows what happened.
                raise Exception('An unknown error occurred.')
    # Statistics
    successes = len(y)
    timeouts = len(yt)
    lat_min = min(y)
    lat_avg = sum(y) / successes
    lat_max = max(y)
    pkt_loss = timeouts / (timeouts + successes) * 100
    # Writing text to image:
    figure = plt.figure()
    figure.suptitle(hostname, fontsize=12, fontweight='bold')
    axis = figure.add_subplot(111)
    figure.subplots_adjust(top=0.85)
    axis.set_title('Min: {:.0f}ms, Max: {:.0f}ms, Avg: {:.0f}ms, Loss: {:.2f}%'
                   .format(lat_min, lat_max, lat_avg, pkt_loss), fontsize=10)
    axis.set_xlabel('Date / Time')
    axis.set_ylabel('Latency (ms)')
    # Plotting parameters here.
    axis.plot(x, y, 'b-', label='Success')
    axis.plot(xt, yt, 'r.', label='Timeout')
    axis.legend()
    axis.set_ylim(ymin=0)
    # Change x-axis to datetime format.
    figure.autofmt_xdate()
    fmt = dates.DateFormatter('%d/%m %H:%M')
    axis.xaxis.set_major_formatter(fmt)
    plt.savefig(hostname + '.png', dpi=500)
    with open(filename, 'a') as file:  # Writes statistics to end of the .log file:
        file.write('\nTest statistics:\n')
        file.write('Min = {:.0f}ms\nMax = {:.0f}ms\nAvg = {:.0f}ms\nLoss = {:.2f}%'
                   .format(lat_min, lat_max, lat_avg, pkt_loss))


def package():
    """After tests are complete, packages all relevant files together into subdirectory
    and creates a .zip archive of that directory.
    """
    computer_name = Popen(['hostname'], stdout=PIPE)  # Discover hostname of PC to name new directory.
    for line in computer_name.stdout:
        computer_name = str(line)[2:-5]  # Remove other characters, save only the hostname.
    # Name of new directory is {computer_name}_{date}_({time}):
    dir_name = computer_name + '_' + str(datetime.now().strftime("%d%m%Y(%H.%M)"))
    file_name = dir_name + '.zip'
    system('md ' + dir_name)  # Make new directory
    system('move *.log ' + dir_name)  # Moves all files ending in '.log' to new directory.
    system('move *.txt ' + dir_name)  # Moves all files ending in '.txt' to new directory.
    system('move *.png ' + dir_name)  # Moves all files ending in '.png' to new directory.
    with ZipFile(file_name, 'w', ZIP_DEFLATED) as zf:  # Create new .zip file with same name as new directory.
        for root, dirs, files in walk(dir_name):
            for file in files:
                zf.write(path.join(root, file))  # Write new directory to .zip file.
    system('move {} {}'.format(file_name, dir_name))  # Move .zip file into new directory.
    page_refresh()
    print('Tests have completed successfully.\nScript will exit in 5 seconds.')
    sleep(5)
    page_refresh()
    sysexit()  # Tests are complete. Quit program.


def one(runtime, hostname):
    """Perform ping test on single specified host"""
    page_refresh()
    print('Testing {}\n'.format(hostname))
    print('Writing information about your system into "sysinfo.txt"...')
    with open('sysinfo.txt', 'w+') as file:  # Write system/test information to a .txt file using Windows commands:
        Popen(['tracert', hostname], stdout=file).wait()
        Popen('systeminfo | find /V /I "hotfix" | find /V "KB"', shell=True, stdout=file).wait()
        Popen(['ipconfig', '/all'], stdout=file).wait()
    print('Done!')
    test(hostname, runtime)  # Run test() on host.
    package()  # Package all relevant files together and exit program.


def two(runtime, hosts):
    """Performs ping test on multiple unique hosts, specified in 'hosts' list."""
    page_refresh()
    print('Script will now test the following hosts:')
    for host in hosts:
        print(host)
    print('\nWriting information about your system into "sysinfo.txt"...')
    with open('sysinfo.txt', 'w+') as file:  # Write system/test information to a .txt file using Windows commands:
        Popen('systeminfo | find /V /I "hotfix" | find /V "KB"', shell=True, stdout=file).wait()
        Popen(['ipconfig', '/all'], stdout=file).wait()
        print('Done!')
    print('\nThis test will take around {} minutes to complete.'.format(len(hosts * runtime)))
    for host in hosts:  # Append traceroute of host to 'sysinfo.txt' file.
        with open('sysinfo.txt', 'a+') as file:
            Popen(['tracert', host], stdout=file).wait()
        test(host, runtime)  # Perform test() on host.
    package()  # Package all relevant files together and exit program.


def three(runtime, hostname):
    """Finds each device in a traceroute to 'hostname'. Performs ping test on each device."""
    page_refresh()
    print('Testing each device between this PC and {}'.format(hostname))
    print('Checking that hosts are active...')
    trace = Popen(['tracert', '-d', hostname], stdout=PIPE)  # Performs traceroute (IP addresses only) to hostname.
    hosts = []
    for line in trace.stdout:  # Reads output of above traceroute.
        if str(line)[34:-6] != '':  # If line is not empty.
            hosts.append(str(line)[34:-6])  # Append hostname part of line to 'hosts' list.
    del hosts[0]  # Remove first line of traceroute from 'hosts' list.
    non_respond = []
    print('\nDiscovered devices:')
    for hostname in hosts:  # Checks that host responds to pings before testing it.
        if host_check(hostname) is True:
            print(hostname)
        elif host_check(hostname) is False:
            print('"{}" is not responding.'.format(hostname))
            non_respond.append(hostname)  # Add non-responsive hosts to another list.
    for line in non_respond:  # Removes any hostname that appears in list(non_respond) from list(hosts).
        hosts.remove(line)
    print('Done!')
    print('\nWriting information about your system into "sysinfo.txt"...')
    with open('sysinfo.txt', 'w+') as file:  # Write system/test information to a .txt file using Windows commands:
        Popen(['tracert', hostname], stdout=file).wait()  # Output of traceroute to destination.
    if len(non_respond) > 0:  # If there are unresponsive hosts, write them after traceroute:
        with open('sysinfo.txt', 'a') as file:
            file.write("\nUnresponsive Devices:\n")
            for host in non_respond:
                file.write(host + " did not respond\n")  # Write unresponsive hosts to 'sysinfo.txt' file.
    with open('sysinfo.txt', 'a') as file:
        Popen('systeminfo | find /V /I "hotfix" | find /V "KB"', shell=True, stdout=file).wait()  # System information.
        Popen(['ipconfig', '/all'], stdout=file).wait()  # Network card information.
    print('Done!')
    print('\nThis test will take around {} minutes to complete.'.format(len(hosts * runtime)))
    for hostname in hosts:  # Run test() on all devices that appear in 'hosts' list.
        test(hostname, runtime)
    package()  # Package all relevant files together and exit program.


def menu(runtime):
    """Menu system for user interaction."""
    page_refresh()
    sleep(1)
    print('1) Ping a single host for the default time.')  # Run one()
    print('2) Ping a number of hosts, each for the default time.')  # Run two()
    print('3) Ping each host in a path for the default time.')  # Run three()
    print('4) Change the default time (currently: {} minutes).'.format(runtime))  # Changes 'runtime'
    print('0) Exit')  # Quit program.
    selection = input('\nPlease select one of the options above: ')  # User chooses an option and runs function.
    if selection == '1':
        hostname = input('\nEnter the destination address/hostname: ')
        if host_check(hostname) is True:  # If host is active, run one() test.
            one(runtime, hostname)
        elif host_check(hostname) is False:  # If host inactive, restart menu()
            print('{} is not responsive.'.format(hostname))
            reset_session(runtime)
    elif selection == '2':
        hosts = []
        if not path.exists('hosts.txt'):  # Look for hosts file. If it doesn't exist user must input hosts.
            num_hosts = int(input('Enter the number of hosts to test: '))  # How many hosts to add.
            for n in range(num_hosts):
                number = n + 1
                hostname = input('Enter the address/hostname of host #{}: '.format(number))
                with open('hosts.txt', 'a+') as file:  # Write user input to 'hosts.txt' file.
                    file.write(hostname)
                    file.write('\n')
        with open('hosts.txt', 'r') as file:  # Read from 'hosts.txt' file and append to hosts[]
            for line in file.readlines():
                hostname = line.strip('\n')  # Removes newline character.
                if host_check(hostname) is True:  # If host is active, add to hosts[]
                    hosts.append(hostname)
                elif host_check(hostname) is False:  # If host inactive, do not add to list. Do not test.
                    print('{} is not responsive.'.format(hostname))
        two(runtime, hosts)  # Perform two() test on all hosts[]
    elif selection == '3':
        hostname = input('\nPlease enter the destination address/hostname: ')  # User enters endpoint destination.
        if host_check(hostname) is True:  # If endpoint is active, run three()
            three(runtime, hostname)
        elif host_check(hostname) is False:  # If endpoint is inactive, restart menu()
            print('{} is not responsive.'.format(hostname))
            reset_session(runtime)
    elif selection == '4':
        mod_runtime = int(input('Enter the time (in minutes) to run each test: '))  # User enters minutes to run test.
        menu(mod_runtime)  # Restart menu() with new runtime.
    elif selection == '0':
        system('cls')  # Clear the screen.
        sysexit()  # Quit program.
    else:  # If user enters an invalid option, tell them that, then restart menu()
        print('Your selection did not match one of the options provided!')
        reset_session(runtime)


def main():
    """Determines how script will be run. Either menu mode, or command line argument mode.
    Also deals with command line argument conditions.
    """
    if len(argv) == 1:  # No arguments parsed to program, run menu() with default time of 15 mins.
        menu(15)
    elif len(argv) > 1:  # Arguments have been parsed, save variables and pass to functions.
        test_run = argv[1]  # First argument after script name is which runtime option to use.
        runtime = int(argv[2])  # Second argument is time (in minutes) to run test.
        if test_run == '1':
            hostname = argv[3]  # Third argument onwards is hostnames.
            if host_check(hostname) is True:  # If host is active, run one()
                one(runtime, hostname)
            elif host_check(hostname) is False:  # If host inactive, say that then exit program.
                print('{} is not responsive.'.format(hostname))
                sleep(1)
                sysexit()
        elif test_run == '2':
            hosts = []
            if not path.exists('hosts.txt'):  # Reads arguments if 'hosts.txt' file is not present.
                for hostname in argv[3:]:
                    if host_check(hostname) is True:
                        hosts.append(hostname)
                    elif host_check(hostname) is False:
                        print('\n{} is not responsive.\n'.format(hostname))
            elif path.exists('hosts.txt'):  # Reads hosts from 'hosts.txt' file, ignoring host arguments.
                with open('hosts.txt', 'r') as file:
                    for line in file.readlines():
                        hostname = line.strip('\n')
                        if host_check(hostname) is True:  # If host is active, append to hosts[]
                            hosts.append(hostname)
                        elif host_check(hostname) is False:  # If host inactive, do not add to list. Do not test.
                            print('{} is not responsive.'.format(hostname))
            if len(hosts) > 0:  # If at least one host is active, run two()
                two(runtime, hosts)
            elif len(hosts) == 0:  # If no hosts were active, quit program.
                print('The hosts provided did not respond.')
                sleep(1)
                sysexit()
        elif test_run == '3':
            hostname = argv[3]  # Third argument is endpoint hostname.
            print('Checking endpoint host...')
            if host_check(hostname) is True:  # If endpoint is active, run three()
                three(runtime, hostname)
            elif host_check(hostname) is False:  # If endpoint is inactive, quit program.
                print('{} is not responsive.'.format(hostname))
                sleep(1)
                sysexit()
        else:  # If user entered invalid option, tell them that, then quit.
            page_refresh()
            print('Invalid argument encountered!\nQuitting program..')
            sleep(1)
            sysexit()


main()
