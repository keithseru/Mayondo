from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils.timezone import now
from django.db import transaction
import csv
from datetime import datetime, timedelta
from .models import Sale, Customer, SaleItem 

# Create your views here.
