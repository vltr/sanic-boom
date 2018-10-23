Changelog
=========

v0.1.2 on 2018-10-23
--------------------

* Added ``components`` property on ``BoomRequest`` so any request "leftover" may be handled property (like an open database connection).

v0.1.1 on 2018-10-18
--------------------

* Fixed a bug where handlers derived from ``HTTPMethodView`` class were not being executed (for their signature actually be ``*args, **kwargs``).


v0.1.0 on 2018-10-17
--------------------

* First release on PyPI. (Probably) not stable.
