#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, getopt, csv, os, html.parser, math
import pandas as pd
import numpy as  np
from datetime import datetime
from datetime import timezone
from tzlocal import get_localzone
import calendar

def get_ax_link(row, lat, lon):
    # format example: https://globe.adsbexchange.com/?icao=a4a567&lat=42.397&lon=-71.177&zoom=12.0&showTrace=2020-08-12
    try:
        falink = 'https://globe.adsbexchange.com/?icao='  + row[0].lower() + '&lat=' + str(lat) + '&lon=' + str(lon) + '&zoom=12'
        dt_string = row[4] + ' ' + row[5][:-4]
#        naive = datetime.strptime(dt_string, "%Y/%m/%d %H:%M:%S")
#        local_dt = get_localzone().localize(naive)
#        utc_tuple = local_dt.utctimetuple()
        local = naive.replace(tzinfo=datetime.now(timezone.utc).astimezone().tzinfo)
        utc = local.astimezone(tz=timezone.utc)
        utc_tuple=utc.timetuple()
        falink = falink + '&showTrace=' + str(utc_tuple[0]) + '-' + str.zfill(str(utc_tuple[1]), 2) + '-' + str.zfill(str(utc_tuple[2]), 2)
        epoch_seconds = int(utc.timestamp())
        falink = falink + '&timestamp=' + str(epoch_seconds)

    except:
        falink = falink + '&showTrace=' + row[4][0:4] + '-' + row[4][5:7] + '-' + row[4][8:10]

    return falink

def main(argv):

    inputfile = ''
    outputfile = ''
    lat = 42.3966
    lon = -71.1773
    dist = 2
    verbose = 0
    maxalt = 99999
    logfile = ''
    outfile = '/dev/stdout'
    tday = False
    goodcount=0
    badcount=0
    calcdist = False
    trackservice = 'adsbexchange'
    distunit="mi"
    altcorr = 0

    now_utc = datetime.now(timezone.utc)
    now = now_utc.astimezone(get_localzone())

    try:
       opts, args = getopt.getopt(argv,'',["h","help","?","distance=","lat=","lon=","dist=","log=","logfile=","v","verbose","outfile=","maxalt=","calcdist","distunit=","trackservice=","altcorr="])
    except getopt.GetoptError:
       print('Usage: planefence.py [--verbose] [--calcdist] --distance=<distance_in_statute_miles> --logfile=/path/to/logfile [--outfile=/path/to/outputfile] [--maxalt=maximum_altitude_in_ft] [--format=csv|html|both] [--trackservice=adsbexchange|flightaware]')
       sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "-?", "--help", "--?") :
            print('Usage: planefence.py [--verbose] [--calcdist] --distance=<distance_in_statute_miles> --logfile=/path/to/logfile [--outfile=/path/to/outputfile] [--maxalt=maximum_altitude_in_ft] [--format=csv|html|both] [--trackservice=adsbexchange|flightaware]')
            print('If lat/long is omitted, then Belmont, MA (town hall) is used.')
            print('If distance is omitted, then 2 miles is used.')
            print('If outfile is omitted, then output is written to stdout. Note - if you intend to capture stdout for processing, make sure that --verbose=1 is not used.')
            print('If --today is used, the logfile is assumed to be the base format for logs, and we will attempt to pick today\'s log.')
            print('If --calcdist is used, it will calculate the distance based on the coordinates. If it is omitted, the distance from the logfile will be used. Note that calculation of distances is very processor intensive and may dramatically slow down the processing speed of large files.')
        elif opt == "--lat":
            lat = float(arg)
        elif opt =="--lon":
            lon = float(arg)
        elif opt in ("--logfile", "--log"):
            logfile = arg
        elif opt in ("--distance", "--dist"):
            dist = float(arg)
        elif opt in ("--v", "--verbose"):
            verbose = 1
        elif opt == "--outfile":
            outfile = arg
        elif opt == "--maxalt":
            maxalt = float(arg)
        elif opt == "--calcdist":
            calcdist = True
        elif opt == "--distunit":
            distunit = arg
        elif opt == "--trackservice":
            trackservice = arg
        elif opt == "--altcorr":
            altcorr = int(arg)

    if verbose == 1:
       # print 'lat = ', lat
       # print 'lon = ', lon
       print('max distance = ', dist, distunit)
       print('max altitude = ', maxalt)
       # print 'output is written to ', outfile

    if logfile == '':
       print("ERROR: Need logfile parameter")
       sys.exit(2)

    if verbose == 1:
       print('input is read from ', logfile)

    if trackservice != 'adsbexchange' and trackservice != 'flightaware':
       print("ERROR: --trackservice parameter must be adsbexchange or flightaware")
       sys.exit(2)

    if distunit != 'km' and distunit != "nm" and distunit != "mi" and distunit != "m":
       print("ERROR: --distunit must be one of [km|nm|mi|m]")
       sys.exit(2)

    if int(altcorr) < 0:
       print("ERROR: --altcorr must be a non-negative integer")
       sys.exit(2)

    lat1 = math.radians(float(lat))
    lon1 = math.radians(float(lon))

    # now we open the logfile
    # and we parse through each of the lines
    #
    # format of logfile is 0-ICAO,1-altitude,2-latitude,3-longitude,4-date,5-time,6-angle,7-distance,8-squawk,9-ground_speed(kilometerph),10-track,11-callsign
    # format of airplaneslist is [[0-ICAO,11-FltNum,4/5-FirstHeard,4/5-LastHeard,1-LowestAlt,7-MinDistance,FltLink)]

    with open(logfile, "rt") as f:
        # the line.replace is because sometimes the logfile is corrupted and contains zero bytes. Python pukes over this.
        reader = csv.reader( (line.replace('\0','') for line in f) )
        records = np.array(["ICAO","Flight Number","In-range Date/Time","Out-range Date/Time","Lowest Altitude","Minimal Distance","Flight Link"], dtype = 'object')
        counter = 0
        fltcounter = 0
        for row in reader:
            rowdist=float("999999")
            rowalt=float("999999")

            if len(row[0]) == 6:
                # first safely convert the distance and altitude values from the row into a float.
                # if we can't convert it into a number (e.g., it's text, not a number) then substitute it by some large number
               try:
                   rowdist=float(row[7])
               except:
                   pass

               try:
                   rowalt=float(row[1])-float(altcorr)
               except:
                   pass

            # now check if it's a duplicate that is in range
            if row[0] in records and rowdist <= dist and rowalt <= maxalt:

                # first check if we already have a flight number. If we don't, there may be one in the updated record we could use?
                if records[np.where(records == row[0])[0][0]][1] == "" and row[11].strip() != "":
                    records[np.where(records == row[0])[0][0]][1] = row[11].strip()

                if trackservice == 'flightaware':
                    falink = 'https://flightaware.com/live/modes/' + row[0].lower() + '/ident/' + row[11].strip() + '/redirect'

                if trackservice == 'adsbexchange':
                    # format example: https://globe.adsbexchange.com/?icao=a4a567&lat=42.397&lon=-71.177&zoom=12.0&showTrace=2020-08-12
                    falink = get_ax_link(row, lat, lon)

                records[np.where(records == row[0])[0][0]][6] = falink.strip()

                # replace "LastHeard" by the time in this row:
                records[np.where(records == row[0])[0][0]][3] = row[4] + ' ' + row[5][:8]

                # only replace the lowest altitude if it's smaller than what we had before
                if rowalt < float(records[np.where(records == row[0])[0][0]][4]):
                    # records[np.where(records == row[0])[0][0]][4] = row[1]
                    records[np.where(records == row[0])[0][0]][4] = "{:.0f}".format(rowalt)

                # only replace the smallest distance if it's smaller than what we had before
                if rowdist < float(records[np.where(records == row[0])[0][0]][5]):
                    records[np.where(records == row[0])[0][0]][5] =  "{:.1f}".format(rowdist)

            elif rowdist <= dist and rowalt <= maxalt:
                # it must be a new record. First check if it's in range. If so, write a new row to the records table:
                if verbose == 1:
                    print(counter, row[0], row[11].strip(), "(", rowdist, "<=", dist, ", alt=", rowalt, "): new")
                    counter = counter + 1

                if trackservice == 'flightaware':
                    falink = 'https://flightaware.com/live/modes/' + row[0].lower() + '/ident/' + row[11].strip() + '/redirect'

                if trackservice == 'adsbexchange':
                    falink = get_ax_link(row, lat, lon)

                records=np.vstack([records, np.array([row[0],row[11].strip(), row[4] + ' ' + row[5][:8], row[4] + ' ' + row[5][:8],"{:.0f}".format(rowalt),"{:.1f}".format(rowdist),falink.strip() ])])
                fltcounter = fltcounter + 1

            elif row[0] in records and records[np.where(records == row[0])[0][0]][1] == "" and row[11].strip() != "":
                # we have the record, but it doesn't have a flight number and we now can add it
                records[np.where(records == row[0])[0][0]][1] = row[11].strip()
                if verbose == 1:
                    print("added flight number", row[11].strip(), "for", row[0])


        # Now, let's start writing everything to a CSV and/or HTML file:
        # Step zero - turn string truncation off
        pd.set_option('display.max_colwidth', None)

        # delete the header as this interferes with appending:
        records = np.delete(records, (0), axis=0)

        # Write CSV file
        if fltcounter > 0:
            # make sure that the file has the correct extension
            if verbose == 1:
                print('Output is written to: ', outfile)

            # Now write the table to a file as a CSV file
            with open(outfile, 'w') as file:
                writer = csv.writer(file, delimiter=',')
                writer.writerows(records.tolist())
        else:
            if verbose == 1:
                print('Nothing to write to: ',outfile)

        # That's all, folks!


# this invokes the main function defined above:
if __name__ == "__main__":
    main(sys.argv[1:])
