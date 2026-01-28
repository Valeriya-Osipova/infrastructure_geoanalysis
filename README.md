# infrastructure_geoanalysis
A Python-based algorithm for automated assessment of social infrastructure (kindergartens, schools, clinics) accessibility compliance in rural/low-density areas. Uses isochrone modeling with OpenStreetMap data to:

- Identify zones violating accessibility standards

- Propose optimal locations for new facilities

- Validate against regulatory requirements and empirical spatial patterns

Tested on real data from Northwestern Russia, achieving 72-85% accuracy in location recommendations. Built with GeoPandas, OSMnx, and NetworkX.

Key features:

- Isochrone-based accessibility analysis (pedestrian/transport)

- Regulatory compliance checking (Russian standards SP 42.13330.2016)

- Automated site selection optimization

- Empirical validation on rural settlement patterns

This tool supports territorial planning decisions by providing data-driven insights into infrastructure gaps and placement opportunities.
