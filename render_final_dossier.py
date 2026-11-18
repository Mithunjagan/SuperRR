"""Render the Round 1 dossier with the frozen submission rankings."""
import csv
import json
import os
from datetime import date
from functools import partial
from html import escape
from pathlib import Path
import reportlab
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Group, Line, Circle, Rect, String

ROOT=Path('output/final_recheck')
LEVERAGE=Path('output/leverage_analysis')
INK=HexColor('#14253D'); MUTED=HexColor('#4B5D73'); PINK=HexColor('#AD2364')
PALE=HexColor('#F0F4F8'); GRID=HexColor('#D6DFE9'); BLUE=HexColor('#235D91')
W=A4[0]-92
TRADE_DATE = date(2026, 11, 17)
IPL_TRADE = 'https://www.iplt20.com/news/article/mohd-shami-and-m-siddharth-traded-to-rajasthan-royals-sam-curran-traded-to-lucknow-super-giants'
RR_RETENTION = 'https://www.rajasthanroyals.com/latest-news/ipl-2027-rr-players-retention-list-retained-released'
PBKS_RETENTION = 'https://www.punjabkingsipl.in/news/ipl-2027-meet-our-retained-shers'
RR_TRADE = 'https://www.rajasthanroyals.com/latest-news/ipl-2027-trade-rr-mohammed-shami-manimaran-siddharth'


def register_fonts():
    windows_fonts = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    liberation = Path('/usr/share/fonts/truetype/liberation2')
    packaged = Path(reportlab.__file__).parent / 'fonts'
    font_pairs = [
        (windows_fonts / 'arial.ttf', windows_fonts / 'arialbd.ttf'),
        (liberation / 'LiberationSans-Regular.ttf', liberation / 'LiberationSans-Bold.ttf'),
        (packaged / 'Vera.ttf', packaged / 'VeraBd.ttf'),
    ]
    regular, bold = next(pair for pair in font_pairs if all(path.is_file() for path in pair))
    pdfmetrics.registerFont(TTFont('DossierSans', str(regular)))
    pdfmetrics.registerFont(TTFont('DossierSans-Bold', str(bold)))
    pdfmetrics.registerFontFamily('DossierSans', normal='DossierSans', bold='DossierSans-Bold')

RR_ROLES = {
    'Batters': {
        'Heinrich Klaasen': (
            'Hetmyer or Ferreira slot',
            'If a finishing slot opens, add a right-handed boundary hitter behind Jurel and Parag. He struck at 198.0 across 393 death balls.'),
        'Reeza Hendricks': (
            'Jaiswal / Sooryavanshi cover',
            'T20I watchlist for opening depth. He opened in 31 screened innings. Require IPL evidence before escalating.'),
        'Shubman Gill': (
            'Jaiswal / Sooryavanshi cover',
            'If an opening slot opens, he can bat past the powerplay. His pressure sample includes 81 IPL balls. The chase-only match screen fails.'),
        'Shreyas Iyer': (
            'Jurel / Parag at No. 3-4',
            'Give RR cover at No. 3-4 when an early wicket exposes the middle order. He led the chase-only ranking.'),
        'Mark Chapman': (
            'Left-handed cover ahead of Dubey',
            'T20I watchlist for left-handed rebuild cover. Collapse situations account for 82 of 130 pressure balls. Require IPL evidence before escalating.'),
        'Suryakumar Yadav': (
            'Jurel / Parag at No. 3-4',
            'Add middle-over acceleration if a No. 3-4 slot opens. He struck at 167.1 across 1,661 middle-over balls.'),
        'Nicholas Pooran': (
            'Hetmyer finishing slot',
            'Replace left-handed boundary hitting if Hetmyer leaves. He struck at 191.8 across 427 death balls and ranked fourth in chases.'),
        'Namboori Tilak Varma': (
            'Left-hand partner for Parag or Jurel',
            'Add a left-handed No. 4-5 so RR can keep a left-right pair after the powerplay. He struck at 190.1 across 525 death balls.'),
        'Virat Kohli': (
            'Jaiswal / Sooryavanshi cover',
            'If an opening slot opens, add a batter who can carry the chase into the middle. He faced 100 qualifying chase balls.'),
        'Jos Buttler': (
            'Jaiswal / Sooryavanshi cover',
            'Restore powerplay scoring if an opening slot opens and RR has room for an overseas opener. He struck at 148.3 across 1,206 powerplay balls.'),
    },
    'Bowlers': {
        'Akeal Hosein': (
            'Overseas new-ball spin alongside Siddharth',
            'He bowled 744 legal powerplay balls. Siddharth adds Indian cover in that phase, so an overseas slot needs a clear role beyond duplicating that cover.'),
        'Jasprit Bumrah': (
            'New-ball and death benchmark',
            'Retained by MI. He bowled 696 legal powerplay balls and 514 at the death and led the chase-only ranking.'),
        'Sunil Narine': (
            'Offspin alongside Jadeja',
            'Add a middle-over offspin option if RR has an overseas slot. He bowled 1,068 legal balls in that phase.'),
        'Varun Chakravarthy': (
            'Bishnoi / Punja wicket role',
            'If a domestic spin slot opens, add a middle-over wicket option alongside Jadeja. He took 90 credited wickets on 1,416 legal balls in that phase.'),
        'Jason Holder': (
            'Curran seam cover',
            'Consider for the seam portion of Curran’s all-round role. Holder bowled 546 legal powerplay balls, 711 in the middle and 617 at the death. Assess batting separately.'),
        'Mohammad Nawaz': (
            'Jadeja left-arm spin cover',
            'Consider only if the left-arm spin role opens and eligibility is confirmed. He bowled 750 legal middle-over balls and has zero qualifying IPL pressure balls.'),
        'Rashid Khan': (
            'Bishnoi / Punja wicket role',
            'Add a legspin wicket option with late-over cover if an overseas slot opens. He bowled 1,895 legal middle-over balls and 516 at the death.'),
        'Naveen ul Haq': (
            'Archer / Burger pace cover',
            'If an overseas pace slot opens, prioritise closing overs alongside Shami. He bowled 330 legal powerplay balls and 306 at the death.'),
        'Mitchell Santner': (
            'Jadeja cover alongside Siddharth',
            'Consider if a left-arm spin role and overseas slot open. He bowled 1,158 legal middle-over balls and 312 in the powerplay.'),
        'Jofra Archer': (
            'Existing RR pace role',
            'RR retained him. Keep him as the lead death option. Across 15 screened RR matches he bowled 198 powerplay balls and 102 at the death.'),
    },
}

def render():
    register_fonts()
    audit=json.loads((ROOT/'audit.json').read_text(encoding='utf-8'))
    final=json.loads((ROOT/'final_rankings.json').read_text(encoding='utf-8'))
    leverage=json.loads((LEVERAGE/'results.json').read_text(encoding='utf-8'))
    with (LEVERAGE/'calibration.csv').open(encoding='utf-8',newline='') as f:
        calibration=[row for row in csv.DictReader(f) if row['period']=='2026 holdout'
                     and row['innings']=='0' and row['model']==leverage['selected_model']]
    with (LEVERAGE/'bowl_rankings.csv').open(encoding='utf-8',newline='') as f:
        pooled_leverage={row['name']:row for row in csv.DictReader(f) if row['analysis']=='Primary'}
    top={role:final['roles'][role]['ranking'] for role in ['Batters','Bowlers']}
    lookup={role:{r['name']:r for r in audit['roles'][role]['ranking']} for role in top}
    with (ROOT/'ipl_2027_availability.csv').open(encoding='utf-8',newline='') as f:
        availability={r['name']:r for r in csv.DictReader(f)}
    checked_on = max(r['checked_on'] for r in availability.values())
    report_date = max(date.fromisoformat(checked_on), TRADE_DATE)
    report_date_label = f'{report_date.day} {report_date:%B %Y}'.upper()
    auction={}
    for role, players in lookup.items():
        players=sorted(players.values(),key=lambda r:r['rank'])
        auction[role]=[
            r for r in players if availability[r['name']]['pool_status']=='Confirmed'
            and availability[r['name']]['retention_status'] not in ('Retained','Retained reported')
        ]
    def released_pending(role):
        return [
            r for r in sorted(lookup[role].values(),key=lambda r:r['rank'])
            if availability[r['name']]['retention_status'] in ('Released','Released reported')
            and availability[r['name']]['pool_status']=='Unknown'
        ]

    styles={}
    for name,size,leading,color,bold,after in [
        ('tag',8.5,11,PINK,True,9),('title',26,30,INK,True,9),('intro',11.5,16,MUTED,False,13),
        ('head',12,16,INK,True,5),('body',10.1,14.3,INK,False,8),('note',8.6,12,MUTED,False,7),
        ('summary_head',13,17,INK,True,5),('summary_body',11.6,17,INK,False,14),
        ('auction_call',11,16,BLUE,False,13),
        ('cell',9,12,INK,False,0),('num',9,12,INK,True,0),('th',8.3,11,white,True,0)]:
        styles[name]=ParagraphStyle(name,fontName='DossierSans-Bold' if bold else 'DossierSans',fontSize=size,
            leading=leading,textColor=color,spaceAfter=after,spaceBefore=7 if name=='head' else 0,
            alignment=TA_RIGHT if name=='num' else 0)
    story=[]
    def p(text,style='body'):story.append(Paragraph(text,styles[style]))
    def section(title,text):p(title,'head');p(text)
    def summary(title,text):p(title,'summary_head');p(text,'summary_body')
    def page(title,subtitle):
        if story:story.append(PageBreak())
        p(f'SUPERR SELECTOR  /  ROUND 1  /  {report_date_label}','tag')
        p(title,'title');p(subtitle,'intro')
    def table(headers,rows,widths,numeric=(),pad=6):
        cells=[[Paragraph(x,styles['th']) for x in headers]]
        cells += [[Paragraph(escape(str(x)),styles['num' if i in numeric else 'cell']) for i,x in enumerate(row)] for row in rows]
        block=Table(cells,colWidths=[x/sum(widths)*W for x in widths],hAlign='LEFT',repeatRows=1)
        block.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,PALE]),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
            ('LINEBELOW',(0,-1),(-1,-1),.5,GRID)]))
        story.append(block);story.append(Spacer(1,8))
    def s(x):return f'{x:+.2f}'
    def rnum(x):return 'NE' if x is None else str(int(x))
    def status(name):
        value=availability[name]['retention_status']
        return {'Retained reported':'Retained*','Released reported':'Released*','Unknown':'Pending'}.get(value,value)
    def footer(c,doc):
        c.setStrokeColor(GRID);c.line(46,40,A4[0]-46,40)
        c.setFont('DossierSans',8);c.setFillColor(MUTED)
        c.drawString(46,26,'SupeRR Selector  |  Historical pressure performance  |  Methodology and evidence')
        c.drawRightString(A4[0]-46,26,str(doc.page))

    page('Round 1 pressure shortlist',
         'Historical leaders: <b>Heinrich Klaasen</b> (batting) and <b>Akeal Hosein</b> (bowling).')
    p("<b>RR auction priority: add finishing depth.</b> RR released Hetmyer and retained Ferreira as internal cover. "
      "Once the pool is published, compare available finishers with a Hetmyer return if he registers. "
      "Klaasen is the historical benchmark and is reported retained by SRH (page 8).",'auction_call')
    p("<b>Bowling: keep Archer at the death and add depth if needed.</b> RR retained Archer. Bumrah leads Hosein "
      "in chases and has 113 qualifying IPL balls to Hosein's 24. MI retained Bumrah and CSK reportedly retained Hosein. Hosein leads the historical rating "
      "by 0.44, with the bootstrap showing a close ordering (page 6).",'auction_call')
    summary('1. Pressure definition',
        'We read the score before each ball. In the first innings, we look for an early collapse. In a chase, we use '
        'balls left, the required rate and wickets in hand to pick out demanding chases that are still on (page 4).')
    summary('2. Performance measurement',
        'Runs off the bat add to a batter\'s score and a dismissal costs them. For bowlers, we credit wickets and deduct runs conceded. '
        'We compare that performance with what we would expect in the same situation, then show how it compares with the player\'s own record outside pressure.')
    summary('3. Fair comparisons',
        'We estimate what a similar ball was worth using earlier IPL and T20I data, with an adjustment for the opponent. Even '
        'after we remove any one match, a player needs at least 60 qualifying balls across at least eight matches.')
    summary('4. Evidence for the top 10',
        'We take out one match at a time and use the lowest score left. Klaasen leads at <b>37.14</b> from a record of '
        '310 balls in 32 matches. Hosein leads at <b>22.10</b>, just ahead of Bumrah at <b>21.66</b>. The full lists are on pages 2-3. '
        'Page 6 explains why other checks favour Bumrah. Pages 9-10 map each player to an RR role.')
    summary('5. Reliability and limitations',
        'Looking at chases alone keeps <b>5 batters and 7 bowlers</b> from the two top tens. The win-probability lists have no names '
        'in common with ours. In 2026, predicting zero beat the ratings for both roles and batting rank correlation was <b>-0.263</b>. '
        'Use the scores to find past performances worth reviewing. Auction decisions also need role, IPL evidence and availability (pages 5-8).')
    leaders=[players[0]['name'] for players in auction.values() if players]
    if leaders:
        p('<b>Confirmed auction shortlist.</b> The highest-rated confirmed names in each available role are '
          + escape(' and '.join(leaders)) + '. See page 8 for the shortlist and RR priorities.','note')
    for role in ['Batters','Bowlers']:
        page('Top 10 '+role.lower(),'The final rating is the lowest score left after we remove each match in turn.')
        rows=[]
        for r in top[role]:
            rows.append([r['final_rank'],r['name'],f"{r['score']:.2f}",f"{r['boot_q0.25']:.2f}",
                f"{r['balls']} / {r['matches']}",r['ipl_balls'],rnum(r['chase_rank']),s(r['lift_per100']),
                status(r['name'])])
        table(['#','Player','Final<br/>rating','Bootstrap<br/>Q25','Balls /<br/>matches','IPL<br/>balls','Chase<br/>rank','Own lift<br/>/ 100','2027<br/>status'],
            rows,[22,108,44,48,51,36,40,43,58],numeric=(0,2,3,4,5,6,7),pad=5)
        p('The final rating uses adjusted contribution per 100 balls, with shrinkage. Bootstrap Q25 is the 25th percentile '
          'of scores from resampling whole matches. Own lift is the unshrunk difference from the player\'s earlier adjusted performance outside pressure. '
          'NE means chase-only ineligible after a match is removed. * marks a reported status. Pending means no verified update in this snapshot.','note')
        if role=='Batters':
            section('Why Klaasen leads',
                'Klaasen came out ahead of expectation in 24 of 32 matches. His best match accounts for 16.9% of his total positive '
                'contribution. He also leads on bootstrap Q25. In chases alone, Iyer leads, followed by Klaasen and Suryakumar Yadav.')
            section('Four selections fail the post-removal chase screen',
                'Hendricks faced 82 qualifying chase balls in six innings. Chapman faced 48 in three. Both have zero qualifying IPL balls '
                'and rely on first-innings collapses to qualify. Gill and Buttler each start with eight qualifying chase innings. '
                'Take one out and they fall to seven, below the required eight. Kohli qualifies and ranks 13th in chases.')
            table(['IPL scouting use','Candidates and evidence'],[
                ['Chase top five and IPL evidence','Iyer, Klaasen, Suryakumar Yadav, Pooran and Tilak Varma.'],
                ['IPL evidence, weaker chase result','Kohli ranks 13th in chases. Gill and Buttler fall below the chase-only eligibility threshold.'],
                ['T20I watchlist','Hendricks and Chapman have zero qualifying IPL balls. Require relevant IPL evidence before escalating.'],
            ],[158,345],pad=4)
            p('Suryakumar placed sixth on the final list. His own lift was -3.11 per 100 balls, so his pressure performance '
              'fell below his earlier baseline.','note')
        else:
            section('How close are Hosein and Bumrah?',
                'Hosein finishes first at 22.10 and Bumrah second at 21.66. Bumrah has the higher bootstrap Q25, leads in chases '
                'and has 113 qualifying IPL balls to Hosein\'s 24. The joint bootstrap leaves plenty of room for either order (page 6).')
            section('Where the bowling evidence comes from',
                'All 239 of Narine\'s qualifying balls came from the IPL. Varun has 319 balls across 38 matches. Nawaz, Naveen and Archer '
                'fall short in chases once a match is removed. Nawaz has zero qualifying IPL balls. His rank reflects his record in the sample, '
                'and his auction eligibility is a separate question.')
            p('Rashid\'s own lift is -1.55 per 100. The appendix looks at Archer\'s squad role and retention separately.','note')

    page('What counts as a pressure ball?','We use the same scoreboard conditions for batters and bowlers.')
    schematic=Drawing(W,157)
    chart_w=W-4
    marked=HexColor('#DCEEBF')
    def label(x,y,value,size=8.6,bold=False,anchor='start'):
        schematic.add(String(x,y,value,fontSize=size,textAnchor=anchor,fillColor=INK,
                             fontName='DossierSans-Bold' if bold else 'DossierSans'))
    def box(x,y,w,color):
        schematic.add(Rect(x,y,w,21,fillColor=color,strokeColor=white,strokeWidth=1.1,rx=3,ry=3))
    label(0,145,'First innings  |  Legal balls already bowled',10,True)
    half=chart_w/2
    box(0,115,half,marked);box(half,115,half,PALE)
    label(half/2,122,'0-59  |  At least 3 wickets lost',anchor='middle')
    label(1.5*half,122,'60-119  |  Outside the window',anchor='middle')
    label(0,92,'Chase  |  Legal balls remaining, from start to finish',10,True)
    quarter=chart_w/4
    box(0,63,half,PALE);box(half,63,quarter,marked);box(half+quarter,63,quarter,marked)
    label(half/2,70,'61-120  |  Outside the window',anchor='middle')
    label(half+quarter/2,70,'31-60 balls',anchor='middle')
    label(half+quarter*1.5,70,'1-30 balls',anchor='middle')
    label(half+quarter/2,48,'9.5-16 runs/over',anchor='middle')
    label(half+quarter*1.5,48,'8-16 runs/over',anchor='middle')
    schematic.add(Line(half+6,37,chart_w-7,37,strokeColor=MUTED,strokeWidth=.55))
    label(half+quarter,23,'Both chase windows need at least 2 wickets in hand',anchor='middle')
    label(0,5,'A ball can qualify in the green bands if it meets the conditions shown.')
    story.append(schematic)
    p('The analysis starts with 184,476 regulation events from 771 matches. Of those, 25,780 meet the pressure definition before we apply '
      'the role and player filters. We excluded revised matches, inconsistent over counts, results that could not be reconciled, the Emerging T20 group and Super Overs.','note')
    p('From a qualifying ball to the final rating','head')
    table(['Step','Calculation','What goes into it'],[
        ['1. Score the ball','Batting: bat runs less dismissal cost. Bowling: credited wicket value less charged runs.',
         'Wicket weights are 8 in the powerplay, 6 in the middle and 4 at the death. No bowling credit for run-outs.'],
        ['2. Adjust for context','Adjusted value = raw value - context expectation - opponent adjustment.',
         'Use earlier dates in the same format, innings and phase. Adjust for balls left, wickets lost and current or required scoring rate.'],
        ['3. Check the player baseline','Own lift = adjusted value - earlier ordinary adjusted rate x exposure.',
         'Ordinary balls sit outside the pressure window. Require 120 earlier ordinary balls. Own lift is reported alongside the rating.'],
        ['4. Remove each match','For each removal: 100 x remaining adjusted value / (remaining balls + 60). Keep the lowest result.',
         'Every removal must leave at least 60 qualifying balls and eight matches. Exact ties use qualifying balls, then player ID.'],
    ],[100,190,213],pad=8)
    p('Bowling exposure counts legal balls and charged runs include wides and no-balls. Batting exposure excludes wides and off-delivery penalties. '
      'An extras-only bowling match can add value without adding exposure. Prior weights and bin edges are on page 11.','note')

    page('The evidence behind the rankings',
         'We checked the win probabilities against match results and asked how much one match could change a player\'s rating.')
    wp=next(row for row in leverage['wp_validation'] if row['period']=='2026 holdout'
            and row['model']==leverage['selected_model'] and row['innings']==0)
    section('How well did the win probabilities match results?',
        f"Across {wp['matches']} matches in the date-separated 2026 sample, log loss was <b>{wp['log_loss']:.3f}</b>. "
        'Guessing 50% every time gave 0.693. The plot shows how often teams actually won at different predicted probabilities.')
    plot=Drawing(W,187)
    x0,y0,side=58,36,139
    def xp(v):return x0+side*v
    def yp(v):return y0+side*v
    for v in (0,.25,.5,.75,1):
        plot.add(Line(xp(v),y0,xp(v),y0+side,strokeColor=GRID,strokeWidth=.55))
        plot.add(Line(x0,yp(v),x0+side,yp(v),strokeColor=GRID,strokeWidth=.55))
        plot.add(String(xp(v),y0-12,f'{v:.0%}',fontName='DossierSans',fontSize=7.5,textAnchor='middle',fillColor=MUTED))
        plot.add(String(x0-8,yp(v)-2,f'{v:.0%}',fontName='DossierSans',fontSize=7.5,textAnchor='end',fillColor=MUTED))
    plot.add(Line(x0,y0,x0+side,y0+side,strokeColor=MUTED,strokeDashArray=[3,3],strokeWidth=.7))
    xy=[(xp(float(row['predicted'])),yp(float(row['actual']))) for row in calibration]
    for (x1,y1),(x2,y2) in zip(xy,xy[1:]):
        plot.add(Line(x1,y1,x2,y2,strokeColor=BLUE,strokeWidth=1))
    for xx,yy in xy:
        plot.add(Circle(xx,yy,3,strokeColor=white,strokeWidth=.5,fillColor=BLUE))
    plot.add(String(x0+side/2,6,'Mean predicted win probability',fontName='DossierSans',fontSize=9,
                    textAnchor='middle',fillColor=INK))
    axis=Group(String(0,0,'Observed win rate',fontName='DossierSans',fontSize=9,textAnchor='middle',fillColor=INK))
    axis.translate(16,y0+side/2);axis.rotate(90)
    plot.add(axis)
    for yy,value,bold in [
        (154,'2026 calibration',True),(136,'Each dot represents one of 10 probability bins.',False),
        (121,'On the diagonal, the predicted and actual rates agree.',False),
        (98,'Close chases had a 35%-65% chance before the ball.',False),
        (83,'Effectively decided means below 5% or above 95%.',False),
        (68,'Late means 18 legal balls or fewer left.',False),
        (45,'See page 7 for how the 2026 sample was used.',True),
    ]:
        plot.add(String(221,yy,value,fontSize=9,fillColor=INK,fontName='DossierSans-Bold' if bold else 'DossierSans'))
    story.append(plot)
    p('<b>Leverage behaves as expected.</b> It flags 836/836 balls in late, close chases and 129/3,175 in late chases that were effectively decided. '
      'We use the same win probabilities to group the chases and calculate leverage, so these counts show how the measure behaves.','note')
    brevis=lookup['Batters']['Dewald Brevis']
    section('What one match did for Brevis',
        'Dewald Brevis topped an earlier version. He scored '
        f"<b>{brevis['pooled']:.2f}</b> with all matches included. One match supplied {brevis['largest_positive_share']:.1%} of his positive contribution. "
        f"Without his most influential match, he fell to <b>{brevis['score']:.2f}</b> (No. {brevis['rank']}).")
    table(['Cross-check against final membership','Batters retained','Bowlers retained'],[
        ['Chase-only, with or without history refit','5 / 10','7 / 10'],
        ['Rank by 25th percentile of the match bootstrap','9 / 10','9 / 10'],
        ['Rank by 25th percentile with eight matches per draw','9 / 10','7 / 10'],
    ],[313,95,95],numeric=(1,2),pad=5)
    p('We resample whole matches 20,000 times and keep fitted values and eligibility fixed. Losing one match matters more when a player '
      'has a shorter record. In the eight-match check, every player gets eight draws per sample, which leaves some evidence from larger records unused.','note')

    page('Hosein and Bumrah','Only 0.44 points separate them on the final rating.')
    b=lookup['Bowlers']['Jasprit Bumrah'];h=lookup['Bowlers']['Akeal Hosein']
    table(['Diagnostic','Jasprit Bumrah','Akeal Hosein'],[
        ['Final rating',f"{b['score']:.2f}",f"{h['score']:.2f}"],
        ['Match-bootstrap Q25',f"{b['boot_q0.25']:.2f}",f"{h['boot_q0.25']:.2f}"],
        ['Chase-only rank',int(b['chase_rank']),int(h['chase_rank'])],
        ['IPL qualifying balls',b['ipl_balls'],h['ipl_balls']],
        ['Total balls / positive-exposure matches',f"{b['balls']} / {b['matches']}",f"{h['balls']} / {h['matches']}"],
        ['Positive contribution matches',f"{b['positive_matches']} / {b['matches']}",f"{h['positive_matches']} / {h['matches']}"],
        ['Largest share of summed positive value',f"{100*b['largest_positive_share']:.1f}%",f"{100*h['largest_positive_share']:.1f}%"],
    ],[263,120,120],numeric=(1,2),pad=5)
    p('Hosein came out ahead in a greater share of his matches and got less of his positive contribution from his best match. '
      'Bumrah had more IPL evidence and came out ahead in chases and on bootstrap Q25.')
    frequency=final['leading_bowler_joint_resample']['first_above_second_frequency']
    p(f'When we resampled their 44 distinct fixtures together, Bumrah finished ahead in <b>{100*frequency:.1f}%</b> of 20,000 draws. '
      'The middle 95% of the difference runs from -32.77 to +37.75 adjusted runs per 100 balls. That leaves the lead uncertain.','note')
    section('Bumrah leads the leverage comparisons',
        'These ratings ask how much win probability each bowler added above what we expected for the match situation and the opponent. '
        'The unit is percentage points per ball. Parentheses give each player\'s 95% fixture-bootstrap interval. Each interval for the Bumrah-minus-Hosein gap includes zero.')
    pairs=leverage['rankings']['bowl']['pair']
    def pooled_interval(name):
        row=pooled_leverage[name]
        return f"{s(float(row['rating_pp']))} ({s(float(row['ci_low']))} to {s(float(row['ci_high']))})"

    rows=[]
    for key,name in [('Primary','All qualifying matches'),('IPL only','IPL only'),('Chase only','Chases only')]:
        row=pairs[key]
        ratings=[pooled_interval(player) for player in row['names']] if key=='Primary' else [s(x) for x in row['ratings']]
        rows.append([name,*ratings,s(row['gap_pp']),f"{s(row['ci'][0])} to {s(row['ci'][1])}"])
    table(['Leverage sample','Bumrah','Hosein','Gap','95% gap interval'],
          rows,[119,113,113,46,112],numeric=(1,2,3,4),pad=5)
    p('<b>Why Hosein is first.</b> The submission uses the lowest score left after removing each match in turn. Hosein still leads '
      '22.10 to 21.66 at that worst point. He was positive in 15 of 19 games versus Bumrah\'s 16 of 24. Bumrah has stronger '
      'IPL and chase-only evidence, making him the stronger match for an open new-ball and death pace role.','note')

    page('The 2026 forecast test failed','In both roles, the zero baseline had lower error. Use the submitted order as a historical scouting shortlist.')
    rows=[]
    for role in ['Batters','Bowlers']:
        d=audit['roles'][role]['forward']
        rows.append([role,d['players'],f"{d['zero']['rmse']:.2f}",f"{d['loo']['rmse']:.2f}",
            f"{d['bootstrap_q25']['rmse']:.2f}",f"{d['loo']['spearman']:+.3f}"])
    table(['2026 cohort','Players','Zero<br/>RMSE','Deletion<br/>RMSE','Q25<br/>RMSE','Deletion<br/>Spearman'],
        rows,[107,54,80,90,80,92],numeric=(1,2,3,4,5),pad=8)
    section('What the baseline predicts',
        'Zero predicts that a player will perform in line with the expectation for the match situation and the opponent. Lower RMSE means less error. '
        'The deletion-score forecasts had higher error in both roles, with negative batting rank correlation and near-zero bowling rank correlation.')
    p('We froze the expectations and ordinary histories at 1 January 2026. Players had to qualify in training and record at least 12 pressure balls '
      'across three matches in the test. All comparisons use the same 26 batters or 30 bowlers. We measure error against their later adjusted rate before shrinkage.')
    section('What changes when we use leverage or a player baseline?',
        'The leverage lists share <b>0/10 batters and 0/10 bowlers</b> with the final rankings. Leverage changes which balls count, which outcome we measure '
        'and which sample we score. The pre-2026 leverage ratings also had more forecast error than zero in 2026.')
    p('Players can have different roles or face different situations inside and outside the pressure window. After adjusting for multiple comparisons, '
      'the leverage study found reliable within-player changes for zero of 151 bowlers and zero of 122 batters.','note')
    section('Where the rankings are less certain',
        'A first-innings collapse has no target, and the situation may favour the fielding side. Players on either side can experience the same situation differently. '
        'Page 2 shows who falls short when we use chases alone.')
    p('Using expectations by format and accounting for opponents makes the comparison fairer. How well a T20I record carries over to the IPL is still uncertain. '
      'Pitch, venue, opposition strength, role and phase can all affect a player\'s results. The pooled scores reflect the mix each player actually faced.')
    p('The history requirement leaves out some early appearances. When we resample or remove matches, we hold the fitted scores and player eligibility fixed. '
      'A full rerun that refits expectations and selects players again could produce different results.')
    p('We revised the pressure window and how we combine match scores after examining the results. '
      '<b>The 2026 period has been inspected repeatedly and is not an untouched confirmation sample.</b> '
      'No parameter, rank or adjudication is preregistered. '
      'Future validation requires frozen rules and genuinely new matches.')
    p('The shortlist answers a narrower question: who scored well in the pressure situations we observed, even after removing any one match? '
      'Review those performances for IPL role fit and availability before committing auction budget.','note')

    page('RR auction plan',
         f'Availability checked {report_date.isoformat()}. RR announced a ₹27.05 crore purse, 19 players and six open slots.')
    table(['RR decision','What the latest evidence supports'],[
        ['Prioritise finishing depth','Ferreira provides internal cover. Compare available finishers with a Hetmyer return if he registers. Hetmyer scored 5.85 on 201 qualifying IPL balls and additional T20I evidence.'],
        ['Keep Archer as the lead death bowler','Archer bowled 102 death balls in 15 screened RR matches. Shami adds new-ball pace. Check Ferguson for depth if he registers. His 3.44 overall rating includes a small, net negative IPL pressure sample (40 balls).'],
        ['Cover Curran’s two roles','Curran moves to LSG. Assess lower-order batting and left-arm seam separately before bidding for an all-rounder. Siddharth already supplies Indian left-arm powerplay spin.'],
    ],[160,343],pad=7)
    watchlist = {role: released_pending(role) for role in top}
    for title, groups in [
        ('Confirmed auction pool', auction),
        ('Released players to track', watchlist),
    ]:
        p(title, 'head')
        rows = [
            [role, r['rank'], r['name'], f"{r['score']:.2f}", status(r['name'])]
            for role, players in groups.items() for r in players[:3]
        ]
        if rows:
            table(['Role','Model rank','Player','Rating','2027 status'],
                  rows,[72,69,178,58,126],numeric=(1,3),pad=5)
        elif groups is auction:
            p('No eligible player had verified auction entry in the register at this check.')
        else:
            p('No eligible player had a verified or reported release in this snapshot.')
    p('Klaasen (37.14) is a historical finishing benchmark. Ferreira fell short of scoring eligibility. '
      'A release earns a watchlist place while registration is pending. These recommendations carry no bid-price or purchase forecast. '
      '* marks a reported status. Player-specific sources are recorded with the availability data.','note')
    p(f'<link href="{IPL_TRADE}" color="#235D91">IPL trade advisory</link> | '
      f'<link href="{RR_TRADE}" color="#235D91">RR trade announcement</link> | '
      f'<link href="{RR_RETENTION}" color="#235D91">RR retentions and purse</link> | '
      f'<link href="{PBKS_RETENTION}" color="#235D91">PBKS retention announcement</link> | '
      '<link href="https://www.iplt20.com/news" color="#235D91">IPL announcements</link>','note')

    role_intros = {
        'Batters': "Hetmyer's release opens a finishing role. RR retained Ferreira and the opening pair.",
        'Bowlers': "Shami and Siddharth add new-ball options. RR retained Archer, so focus on depth behind him.",
    }
    for role in ('Batters','Bowlers'):
        page(f'How the {role.lower()} could help RR', role_intros[role])
        rows=[]
        for player in top[role]:
            name=player['name']
            deployment, contribution=RR_ROLES[role][name]
            rows.append([player['final_rank'],name,status(name),deployment,contribution])
        table(['#','Player','2027 status','RR slot or player','What RR could gain'],
              rows,[25,108,59,109,202],numeric=(0,),pad=6)
        if role=='Batters':
            p('Phase totals and strike rates use all screened IPL and T20I balls faced. Strike rates are runs off the bat per 100 balls. '
              'The pressure-ball counts, where shown, use the qualifying sample from page 2. * marks a reported status.','note')
        else:
            p('Phase volumes count legal balls in the screened IPL and T20I matches. The Archer figures refer to the RR subset on page 8. * marks a reported status. '
              'Possible roles depend on player availability, eligibility and squad slots.','note')

    page('Reproducing the analysis',
         'The source package contains the calculations, checks and submission order.')
    section('How to rerun the analysis',
        'Start with the supplied Data Pack. Run <b>python audit_final_recheck.py</b>, then <b>python finalize_recheck.py</b>, '
        'then <b>python render_final_dossier.py</b>. The source archive includes input SHA-256 hashes, match-level adjusted evidence, '
        'the full audit tables and <b>Unstop_Submission_Order.csv</b>. The archive excludes the confidential raw pack.')
    p('The renderer also reads the saved leverage diagnostics and <b>ipl_2027_availability.csv</b>. The availability file covers the full eligible ranking '
      'and RR comparison players. The auction shortlist requires official registration. The release watchlist also records sourced media reports.')
    section('Scoring settings for page 4',
        'Phase priors start with 100 virtual balls at +1 for batting or -1 for bowling. The two match-state tiers borrow 100 and 60 balls. '
        'Opponent and ordinary-player estimates borrow 60 toward zero. Balls-left bins are six balls late and 12 earlier. '
        'Wicket boundaries are 1, 2, 3, 4, 6 and 9. Rate bins are two runs per over, capped at 30.')
    section('What the other leagues showed',
        'The earlier Cricsheet check covered 610 BBL, PSL, SA20 and CPL matches using the older pressure window. Klaasen recorded +30.29 adjusted runs per 100 '
        '(96 balls), Narine +68.68 (64) and Rashid -8.27 (83). These rates describe that sample and carry zero weight in the submitted order.')
    p('Inputs include the supplied Round 1 Problem Statement (pages 1-2), its CSVs and the analysis outputs. '
      '<link href="https://cricsheet.org/downloads/" color="#235D91">Cricsheet dataset source</link>. '
      '<link href="https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758" color="#235D91">Official competition listing</link>.','note')

    destination=Path('output/pdf/SupeRR_Round_1_Scouting_Dossier.pdf')
    destination.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(destination),pagesize=A4,leftMargin=46,rightMargin=46,topMargin=44,bottomMargin=57,
        title='SupeRR Selector | Final pressure shortlist and recheck',author='Mithun Kumar J')
    doc.build(story,onFirstPage=footer,onLaterPages=footer,
              canvasmaker=partial(Canvas,initialFontName='DossierSans'))
    print(destination)

if __name__=='__main__':render()
